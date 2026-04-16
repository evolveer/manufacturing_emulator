"""
Business Rules
Encapsulates domain logic for parameter validation, disposition recommendation,
and batch completeness checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    from .models import Batch, Deviation, ParameterRecord, ParameterSpec, StepExecution

from .enums import DeviationSeverity, DeviationStatus, Disposition, StepStatus


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

def validate_parameter(spec: "ParameterSpec", raw_value: str) -> Tuple[bool, str, object]:
    """
    Validate a raw string value against a ParameterSpec.

    Returns (within_spec, message, typed_value).
    """
    if spec.data_type == "boolean":
        lower = raw_value.strip().lower()
        if lower not in ("pass", "fail", "yes", "no", "true", "false"):
            return False, f"Expected pass/fail, got '{raw_value}'", raw_value
        typed = lower in ("pass", "yes", "true")
        if spec.allowed_values:
            allowed_lower = [v.lower() for v in spec.allowed_values]
            within = lower in allowed_lower
            msg = "" if within else f"Value '{raw_value}' not in allowed set {spec.allowed_values}"
            return within, msg, raw_value

        return True, "", raw_value

    if spec.data_type == "string":
        if spec.allowed_values:
            within = raw_value in spec.allowed_values
            msg = "" if within else f"Value '{raw_value}' not in allowed set {spec.allowed_values}"
            return within, msg, raw_value
        return True, "", raw_value

    # Numeric
    try:
        typed = float(raw_value)
    except ValueError:
        return False, f"Expected a number, got '{raw_value}'", raw_value

    if spec.min_value is not None and typed < spec.min_value:
        return False, f"{typed} is below minimum {spec.min_value} {spec.unit}", typed
    if spec.max_value is not None and typed > spec.max_value:
        return False, f"{typed} is above maximum {spec.max_value} {spec.unit}", typed
    return True, "", typed


# ---------------------------------------------------------------------------
# Disposition recommendation
# ---------------------------------------------------------------------------

def recommend_disposition(
    batch: "Batch",
    executions: List["StepExecution"],
    deviations: List["Deviation"],
    required_step_ids: List[str],
) -> Tuple[Disposition, str, float]:
    """
    Compute a disposition recommendation.

    Returns (Disposition, reason_string, completeness_score 0-100).
    """
    reasons: List[str] = []

    # --- Critical deviations open ---
    critical_open = [
        d for d in deviations
        if d.severity == DeviationSeverity.CRITICAL
        and d.status in (DeviationStatus.OPEN, DeviationStatus.INVESTIGATING, DeviationStatus.ESCALATED)
    ]
    if critical_open:
        reasons.append(f"{len(critical_open)} critical deviation(s) remain open.")
        return Disposition.REJECT_HOLD, "; ".join(reasons), _completeness(executions, required_step_ids)

    # --- Mandatory steps incomplete ---
    completed_step_ids = {
        e.step_id for e in executions if e.status == StepStatus.COMPLETED
    }
    incomplete_required = [sid for sid in required_step_ids if sid not in completed_step_ids]
    if incomplete_required:
        reasons.append(f"{len(incomplete_required)} mandatory step(s) not completed.")
        return Disposition.REJECT_HOLD, "; ".join(reasons), _completeness(executions, required_step_ids)

    # --- Missing required parameters ---
    missing_params: List[str] = []
    for exe in executions:
        recorded_names = {p.name for p in exe.parameters}
        # We cannot check spec here without recipe; rely on within_spec flag
        out_of_spec = [p for p in exe.parameters if not p.within_spec]
        if out_of_spec:
            missing_params.extend([p.name for p in out_of_spec])

    # --- Minor / major deviations with justification ---
    non_critical_open = [
        d for d in deviations
        if d.severity != DeviationSeverity.CRITICAL
        and d.status in (DeviationStatus.OPEN, DeviationStatus.INVESTIGATING)
    ]
    justified = [
        d for d in deviations
        if d.status == DeviationStatus.APPROVED_WITH_JUSTIFICATION
    ]

    score = _completeness(executions, required_step_ids)

    if non_critical_open:
        reasons.append(f"{len(non_critical_open)} non-critical deviation(s) still open.")
        return Disposition.REJECT_HOLD, "; ".join(reasons), score

    if justified or missing_params:
        reasons.append("Minor deviations closed with justification or out-of-spec values noted.")
        return Disposition.RELEASE_WITH_COMMENTS, "; ".join(reasons), score

    return Disposition.RELEASE, "All checks passed.", score


def _completeness(executions: List["StepExecution"], required_step_ids: List[str]) -> float:
    if not required_step_ids:
        return 100.0
    completed = sum(
        1 for e in executions
        if e.step_id in required_step_ids and e.status == StepStatus.COMPLETED
    )
    return round(completed / len(required_step_ids) * 100, 1)
