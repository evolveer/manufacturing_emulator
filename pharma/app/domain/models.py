"""
Domain Models
Pydantic-based domain entities for the pharma batch execution simulator.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import (
    BatchStatus,
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
    Disposition,
    OrderStatus,
    ReviewStatus,
    StepStatus,
)


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Production Order
# ---------------------------------------------------------------------------

class ProductionOrder(BaseModel):
    order_id: str = Field(default_factory=lambda: _new_id("ORD-"))
    product_code: str
    product_name: str
    quantity: float
    unit: str = "kg"
    due_date: str  # ISO date string
    site: str
    status: OrderStatus = OrderStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = "system"
    batch_id_ref: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class ParameterSpec(BaseModel):
    """Specification for a single process parameter within a recipe step."""
    name: str
    unit: str
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None  # for categorical params
    data_type: str = "float"  # float | string | boolean


class RecipeStep(BaseModel):
    step_id: str
    name: str
    sequence: int
    required: bool = True
    expected_duration_min: int = 30  # minutes
    description: str = ""
    parameters: List[ParameterSpec] = Field(default_factory=list)
    acceptance_criteria: str = ""
    allowed_next_statuses: List[StepStatus] = Field(
        default_factory=lambda: [
            StepStatus.IN_PROGRESS,
            StepStatus.COMPLETED,
            StepStatus.DEVIATED,
            StepStatus.SKIPPED,
        ]
    )


class Recipe(BaseModel):
    recipe_id: str
    name: str
    product_code: str
    version: str = "1.0"
    steps: List[RecipeStep] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

class Batch(BaseModel):
    batch_id: str = Field(default_factory=lambda: _new_id("BAT-"))
    order_id: str
    recipe_id: str
    product_code: str
    product_name: str
    site: str
    status: BatchStatus = BatchStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = "system"
    current_step_id: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.NOT_STARTED
    disposition: Disposition = Disposition.PENDING
    deviation_count: int = 0
    quantity: float = 0.0
    unit: str = "kg"
    completed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_comment: Optional[str] = None


# ---------------------------------------------------------------------------
# Step Execution
# ---------------------------------------------------------------------------

class ParameterRecord(BaseModel):
    parameter_id: str = Field(default_factory=lambda: _new_id("PAR-"))
    execution_id: str
    batch_id: str
    step_id: str
    name: str
    value: Any
    unit: str = ""
    within_spec: bool = True
    recorded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    recorded_by: str = "operator"


class StepExecution(BaseModel):
    execution_id: str = Field(default_factory=lambda: _new_id("EXE-"))
    batch_id: str
    step_id: str
    step_name: str
    sequence: int
    status: StepStatus = StepStatus.NOT_STARTED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    operator: str = ""
    comments: str = ""
    parameters: List[ParameterRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deviation
# ---------------------------------------------------------------------------

class Deviation(BaseModel):
    deviation_id: str = Field(default_factory=lambda: _new_id("DEV-"))
    batch_id: str
    step_id: str
    step_name: str = ""
    category: DeviationCategory
    severity: DeviationSeverity
    description: str
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    detected_by: str = "system"
    status: DeviationStatus = DeviationStatus.OPEN
    disposition: Optional[str] = None
    corrective_action: Optional[str] = None
    justification: Optional[str] = None
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Audit Event
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: _new_id("AUD-"))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user: str
    action: str
    entity_type: str
    entity_id: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment: Optional[str] = None


# ---------------------------------------------------------------------------
# Review Decision
# ---------------------------------------------------------------------------

class ReviewDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: _new_id("REV-"))
    batch_id: str
    reviewer: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    disposition: Disposition
    comment: str = ""
    completeness_score: float = 0.0  # 0–100
    open_deviations: int = 0
    critical_deviations: int = 0
    missing_parameters: List[str] = Field(default_factory=list)
    incomplete_steps: List[str] = Field(default_factory=list)
