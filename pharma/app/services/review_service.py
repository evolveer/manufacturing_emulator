"""
Review Service
Computes batch completeness, generates disposition recommendations,
and persists review decisions.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..domain.enums import BatchStatus, DeviationSeverity, DeviationStatus, Disposition, ReviewStatus, StepStatus
from ..domain.models import Batch, Deviation, ReviewDecision, StepExecution
from ..domain.rules import recommend_disposition
from ..utils.persistence import get_by_id, load_all, upsert
from . import audit_service
from .batch_service import get_batch, get_executions_for_batch, update_batch
from .deviation_service import get_deviations_for_batch
from .recipe_service import get_recipe

ENTITY = "review_decisions"


def compute_review(batch_id: str) -> ReviewDecision:
    """Compute a review decision for a batch without persisting it."""
    batch = get_batch(batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    recipe = get_recipe(batch.recipe_id)
    required_step_ids = [s.step_id for s in recipe.steps if s.required] if recipe else []

    executions = get_executions_for_batch(batch_id)
    deviations = get_deviations_for_batch(batch_id)

    disposition, reason, score = recommend_disposition(
        batch, executions, deviations, required_step_ids
    )

    # Missing parameters
    missing_params: List[str] = []
    for exe in executions:
        out_of_spec = [p.name for p in exe.parameters if not p.within_spec]
        missing_params.extend(out_of_spec)

    # Incomplete required steps
    completed_ids = {e.step_id for e in executions if e.status == StepStatus.COMPLETED}
    incomplete_steps = [sid for sid in required_step_ids if sid not in completed_ids]

    open_devs = [
        d for d in deviations
        if d.status in (DeviationStatus.OPEN, DeviationStatus.INVESTIGATING, DeviationStatus.ESCALATED)
    ]
    critical_devs = [d for d in open_devs if d.severity == DeviationSeverity.CRITICAL]

    decision = ReviewDecision(
        batch_id=batch_id,
        reviewer="",
        disposition=disposition,
        comment=reason,
        completeness_score=score,
        open_deviations=len(open_devs),
        critical_deviations=len(critical_devs),
        missing_parameters=list(set(missing_params)),
        incomplete_steps=incomplete_steps,
    )
    return decision


def submit_review(
    batch_id: str,
    reviewer: str,
    disposition: Disposition,
    comment: str = "",
) -> ReviewDecision:
    """Persist a reviewer's disposition decision."""
    decision = compute_review(batch_id)
    decision.reviewer = reviewer
    decision.disposition = disposition
    decision.comment = comment

    upsert(ENTITY, ReviewDecision, decision, "decision_id")

    # Update batch
    batch = get_batch(batch_id)
    if batch:
        batch.review_status = ReviewStatus.COMPLETED
        batch.disposition = disposition
        batch.reviewed_by = reviewer
        batch.review_comment = comment
        if disposition == Disposition.RELEASE:
            batch.status = BatchStatus.RELEASED
        elif disposition == Disposition.REJECT_HOLD:
            batch.status = BatchStatus.REJECTED
        update_batch(batch)

    audit_service.log_event(
        user=reviewer,
        action="batch reviewed",
        entity_type="Batch",
        entity_id=batch_id,
        new_value=disposition.value,
        comment=comment,
    )
    return decision


def get_review_for_batch(batch_id: str) -> Optional[ReviewDecision]:
    decisions = load_all(ENTITY, ReviewDecision)
    matches = [d for d in decisions if d.batch_id == batch_id]
    return matches[-1] if matches else None
