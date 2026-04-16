"""
Deviation Service
Manages non-conformance / deviation records: opening, updating, closing.
"""

from __future__ import annotations

from typing import List, Optional

from ..domain.enums import DeviationCategory, DeviationSeverity, DeviationStatus
from ..domain.models import Batch, Deviation
from ..utils.helpers import now_iso
from ..utils.persistence import get_by_id, load_all, upsert
from . import audit_service

ENTITY = "deviations"


def open_deviation(
    batch_id: str,
    step_id: str,
    step_name: str,
    category: DeviationCategory,
    severity: DeviationSeverity,
    description: str,
    detected_by: str = "system",
) -> Deviation:
    dev = Deviation(
        batch_id=batch_id,
        step_id=step_id,
        step_name=step_name,
        category=category,
        severity=severity,
        description=description,
        detected_by=detected_by,
    )
    upsert(ENTITY, Deviation, dev, "deviation_id")

    # Update batch deviation count
    from .batch_service import get_batch, update_batch
    batch = get_batch(batch_id)
    if batch:
        batch.deviation_count += 1
        update_batch(batch)

    audit_service.log_event(
        user=detected_by,
        action="deviation opened",
        entity_type="Deviation",
        entity_id=dev.deviation_id,
        new_value=DeviationStatus.OPEN.value,
        comment=f"Batch {batch_id}, Step {step_id}: {description[:80]}",
    )
    return dev


def update_deviation_status(
    deviation_id: str,
    new_status: DeviationStatus,
    user: str,
    justification: Optional[str] = None,
    corrective_action: Optional[str] = None,
    disposition: Optional[str] = None,
) -> Optional[Deviation]:
    dev = get_by_id(ENTITY, Deviation, "deviation_id", deviation_id)
    if not dev:
        return None
    old = dev.status.value
    dev.status = new_status
    if justification:
        dev.justification = justification
    if corrective_action:
        dev.corrective_action = corrective_action
    if disposition:
        dev.disposition = disposition
    if new_status == DeviationStatus.CLOSED:
        dev.closed_at = now_iso()
        dev.closed_by = user
    upsert(ENTITY, Deviation, dev, "deviation_id")

    audit_service.log_event(
        user=user,
        action="deviation closed" if new_status == DeviationStatus.CLOSED else "deviation opened",
        entity_type="Deviation",
        entity_id=deviation_id,
        old_value=old,
        new_value=new_status.value,
        comment=justification or corrective_action or "",
    )
    return dev


def get_all_deviations() -> List[Deviation]:
    return load_all(ENTITY, Deviation)


def get_deviations_for_batch(batch_id: str) -> List[Deviation]:
    return [d for d in get_all_deviations() if d.batch_id == batch_id]


def get_deviation(deviation_id: str) -> Optional[Deviation]:
    return get_by_id(ENTITY, Deviation, "deviation_id", deviation_id)
