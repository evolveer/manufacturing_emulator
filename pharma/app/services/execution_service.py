"""
Execution Service
Manages step-by-step batch execution: starting steps, capturing parameters,
completing steps, and triggering deviations on out-of-spec values.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..domain.enums import BatchStatus, DeviationCategory, DeviationSeverity, StepStatus
from ..domain.models import Batch, Deviation, ParameterRecord, StepExecution
from ..domain.rules import validate_parameter
from ..utils.helpers import now_iso
from ..utils.persistence import get_by_id, load_all, upsert
from . import audit_service
from .batch_service import (
    EXEC_ENTITY,
    get_batch,
    get_executions_for_batch,
    update_batch,
    update_execution,
)
from .deviation_service import open_deviation
from .recipe_service import get_recipe

PARAM_ENTITY = "parameters"


def get_execution_for_step(batch_id: str, step_id: str) -> Optional[StepExecution]:
    for exe in get_executions_for_batch(batch_id):
        if exe.step_id == step_id:
            return exe
    return None


def start_step(batch_id: str, step_id: str, operator: str) -> Optional[StepExecution]:
    exe = get_execution_for_step(batch_id, step_id)
    if not exe:
        return None
    if exe.status not in (StepStatus.NOT_STARTED, StepStatus.READY):
        return exe  # already started

    exe.status = StepStatus.IN_PROGRESS
    exe.started_at = now_iso()
    exe.operator = operator
    update_execution(exe)

    batch = get_batch(batch_id)
    if batch:
        batch.status = BatchStatus.IN_PROGRESS
        batch.current_step_id = step_id
        update_batch(batch)

    audit_service.log_event(
        user=operator,
        action="step started",
        entity_type="StepExecution",
        entity_id=exe.execution_id,
        new_value=StepStatus.IN_PROGRESS.value,
        comment=f"Batch {batch_id}, Step {step_id}",
    )
    return exe


def capture_parameters(
    batch_id: str,
    step_id: str,
    param_values: Dict[str, str],
    operator: str,
    recipe_id: str,
) -> Tuple[List[ParameterRecord], List[Deviation]]:
    """
    Validate and persist parameter values for a step.
    Returns (list of ParameterRecords, list of Deviations triggered).
    """
    exe = get_execution_for_step(batch_id, step_id)
    if not exe:
        return [], []

    recipe = get_recipe(recipe_id)
    step_spec = next((s for s in recipe.steps if s.step_id == step_id), None) if recipe else None
    param_specs = {ps.name: ps for ps in step_spec.parameters} if step_spec else {}

    records: List[ParameterRecord] = []
    deviations: List[Deviation] = []

    for name, raw_value in param_values.items():
        spec = param_specs.get(name)
        within_spec = True
        if spec:
            within_spec, msg, typed_value = validate_parameter(spec, raw_value)
        else:
            typed_value = raw_value

        rec = ParameterRecord(
            execution_id=exe.execution_id,
            batch_id=batch_id,
            step_id=step_id,
            name=name,
            value=typed_value,
            unit=spec.unit if spec else "",
            within_spec=within_spec,
            recorded_by=operator,
        )
        upsert(PARAM_ENTITY, ParameterRecord, rec, "parameter_id")
        records.append(rec)

        audit_service.log_event(
            user=operator,
            action="parameter changed",
            entity_type="ParameterRecord",
            entity_id=rec.parameter_id,
            new_value=f"{name}={raw_value}",
            comment=f"Batch {batch_id}, Step {step_id}, within_spec={within_spec}",
        )

        if not within_spec and spec:
            dev = open_deviation(
                batch_id=batch_id,
                step_id=step_id,
                step_name=step_spec.name if step_spec else step_id,
                category=DeviationCategory.OUT_OF_RANGE,
                severity=DeviationSeverity.MAJOR,
                description=f"Parameter '{name}' out of spec: {raw_value} {spec.unit}. {msg}",
                detected_by=operator,
            )
            deviations.append(dev)

    # Refresh exe with parameters
    exe = get_execution_for_step(batch_id, step_id)
    if exe:
        all_params = load_all(PARAM_ENTITY, ParameterRecord)
        exe.parameters = [p for p in all_params if p.execution_id == exe.execution_id]
        update_execution(exe)

    return records, deviations


def complete_step(
    batch_id: str,
    step_id: str,
    operator: str,
    comment: str = "",
) -> Optional[StepExecution]:
    exe = get_execution_for_step(batch_id, step_id)
    if not exe or exe.status != StepStatus.IN_PROGRESS:
        return exe

    exe.status = StepStatus.COMPLETED
    exe.completed_at = now_iso()
    exe.comments = comment
    update_execution(exe)

    # Advance batch to next step
    _advance_batch_step(batch_id, step_id)

    audit_service.log_event(
        user=operator,
        action="step started",  # reuse action name per spec; logged as completion
        entity_type="StepExecution",
        entity_id=exe.execution_id,
        old_value=StepStatus.IN_PROGRESS.value,
        new_value=StepStatus.COMPLETED.value,
        comment=f"Batch {batch_id}, Step {step_id}. {comment}",
    )
    return exe


def mark_step_deviated(
    batch_id: str,
    step_id: str,
    operator: str,
    description: str,
    severity: DeviationSeverity = DeviationSeverity.MAJOR,
    comment: str = "",
) -> Tuple[Optional[StepExecution], Optional[Deviation]]:
    exe = get_execution_for_step(batch_id, step_id)
    if not exe:
        return None, None

    exe.status = StepStatus.DEVIATED
    exe.comments = comment
    if not exe.started_at:
        exe.started_at = now_iso()
    update_execution(exe)

    recipe = get_recipe(get_batch(batch_id).recipe_id if get_batch(batch_id) else "")
    step_name = exe.step_name

    dev = open_deviation(
        batch_id=batch_id,
        step_id=step_id,
        step_name=step_name,
        category=DeviationCategory.MANUAL_ENTRY,
        severity=severity,
        description=description,
        detected_by=operator,
    )

    audit_service.log_event(
        user=operator,
        action="deviation opened",
        entity_type="StepExecution",
        entity_id=exe.execution_id,
        new_value=StepStatus.DEVIATED.value,
        comment=f"Batch {batch_id}, Step {step_id}: {description}",
    )
    return exe, dev


def skip_step(
    batch_id: str,
    step_id: str,
    operator: str,
    reason: str,
    step_required: bool = False,
) -> Tuple[Optional[StepExecution], Optional[Deviation]]:
    exe = get_execution_for_step(batch_id, step_id)
    if not exe:
        return None, None

    exe.status = StepStatus.SKIPPED
    exe.comments = reason
    update_execution(exe)

    dev = None
    if step_required:
        dev = open_deviation(
            batch_id=batch_id,
            step_id=step_id,
            step_name=exe.step_name,
            category=DeviationCategory.SKIPPED_STEP,
            severity=DeviationSeverity.CRITICAL,
            description=f"Mandatory step '{exe.step_name}' was skipped. Reason: {reason}",
            detected_by=operator,
        )
        audit_service.log_event(
            user=operator,
            action="deviation opened",
            entity_type="StepExecution",
            entity_id=exe.execution_id,
            new_value=StepStatus.SKIPPED.value,
            comment=f"Mandatory step skipped: {reason}",
        )

    _advance_batch_step(batch_id, step_id)
    return exe, dev


def _advance_batch_step(batch_id: str, completed_step_id: str) -> None:
    """Move the batch's current_step_id to the next not-started step."""
    batch = get_batch(batch_id)
    if not batch:
        return

    executions = get_executions_for_batch(batch_id)
    found_current = False
    for exe in executions:
        if found_current and exe.status == StepStatus.NOT_STARTED:
            exe.status = StepStatus.READY
            update_execution(exe)
            batch.current_step_id = exe.step_id
            update_batch(batch)
            return
        if exe.step_id == completed_step_id:
            found_current = True

    # All steps done – mark batch completed
    all_done = all(
        e.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.DEVIATED)
        for e in executions
    )
    if all_done:
        from .batch_service import set_batch_status
        set_batch_status(batch_id, BatchStatus.COMPLETED, user="system")
