"""
Batch Service
Manages batch lifecycle: instantiation from orders, status transitions, and retrieval.
Integration hooks fire MES and PCS calls at each lifecycle event.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..domain.enums import BatchStatus
from ..domain.models import Batch, StepExecution
from ..utils.helpers import now_iso
from ..utils.persistence import get_by_id, load_all, upsert
from . import audit_service
from .recipe_service import get_recipe

logger = logging.getLogger("pharma.services.batch")

ENTITY = "batches"
EXEC_ENTITY = "step_executions"


def _fire_integration(fn_name: str, *args, **kwargs) -> None:
    """Call an integration orchestrator function, swallowing all errors."""
    try:
        from ..integration import orchestrator as orch
        getattr(orch, fn_name)(*args, **kwargs)
    except Exception as exc:
        logger.warning("Integration hook %s failed (non-fatal): %s", fn_name, exc)


def create_batch(
    order_id: str,
    product_code: str,
    product_name: str,
    site: str,
    quantity: float,
    unit: str,
    recipe_id: str,
    created_by: str = "mes_operator",
) -> Batch:
    recipe = get_recipe(recipe_id)
    if not recipe:
        raise ValueError(f"Recipe {recipe_id} not found")

    batch = Batch(
        order_id=order_id,
        recipe_id=recipe_id,
        product_code=product_code,
        product_name=product_name,
        site=site,
        quantity=quantity,
        unit=unit,
        created_by=created_by,
    )

    # Initialise step executions
    from ..domain.enums import StepStatus
    executions: List[StepExecution] = []
    for step in sorted(recipe.steps, key=lambda s: s.sequence):
        exe = StepExecution(
            batch_id=batch.batch_id,
            step_id=step.step_id,
            step_name=step.name,
            sequence=step.sequence,
        )
        executions.append(exe)

    if executions:
        batch.current_step_id = executions[0].step_id
        executions[0].status = StepStatus.READY

    upsert(ENTITY, Batch, batch, "batch_id")
    for exe in executions:
        upsert(EXEC_ENTITY, StepExecution, exe, "execution_id")

    audit_service.log_event(
        user=created_by,
        action="batch created",
        entity_type="Batch",
        entity_id=batch.batch_id,
        new_value=BatchStatus.CREATED.value,
        comment=f"Order {order_id}, Recipe {recipe_id}",
    )

    # ── Integration: create MES work order + start PCS machine ────────────
    recipe_steps_info = [
        {"step_id": s.step_id, "name": s.name, "sequence": s.sequence}
        for s in recipe.steps
    ]
    _fire_integration(
        "on_batch_created",
        batch_id=batch.batch_id,
        pharma_order_id=order_id,
        product_code=product_code,
        product_name=product_name,
        quantity=quantity,
        recipe_steps=recipe_steps_info,
    )

    return batch


def get_batch(batch_id: str) -> Optional[Batch]:
    return get_by_id(ENTITY, Batch, "batch_id", batch_id)


def get_all_batches() -> List[Batch]:
    return load_all(ENTITY, Batch)


def update_batch(batch: Batch) -> Batch:
    upsert(ENTITY, Batch, batch, "batch_id")
    return batch


def get_executions_for_batch(batch_id: str) -> List[StepExecution]:
    all_execs = load_all(EXEC_ENTITY, StepExecution)
    return sorted(
        [e for e in all_execs if e.batch_id == batch_id],
        key=lambda e: e.sequence,
    )


def update_execution(exe: StepExecution) -> StepExecution:
    upsert(EXEC_ENTITY, StepExecution, exe, "execution_id")
    return exe


def set_batch_status(batch_id: str, status: BatchStatus, user: str = "system") -> Optional[Batch]:
    batch = get_batch(batch_id)
    if not batch:
        return None
    old = batch.status.value
    batch.status = status
    if status == BatchStatus.COMPLETED:
        batch.completed_at = now_iso()
    upsert(ENTITY, Batch, batch, "batch_id")
    audit_service.log_event(
        user=user,
        action="batch status changed",
        entity_type="Batch",
        entity_id=batch_id,
        old_value=old,
        new_value=status.value,
    )

    # ── Integration hooks ──────────────────────────────────────────────────
    if status == BatchStatus.COMPLETED:
        _fire_integration(
            "on_batch_completed",
            batch_id=batch_id,
            product_code=batch.product_code,
            quantity=batch.quantity,
        )
    elif status == BatchStatus.RELEASED:
        _fire_integration(
            "on_batch_released",
            batch_id=batch_id,
            product_code=batch.product_code,
            quantity=batch.quantity,
        )
    elif status in (BatchStatus.REJECTED, BatchStatus.ON_HOLD):
        _fire_integration(
            "on_batch_rejected",
            batch_id=batch_id,
            reason=f"Batch status set to {status.value}",
        )

    return batch
