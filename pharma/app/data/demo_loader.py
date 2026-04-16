"""
Demo Scenarios Loader
Seeds the runtime database with three pre-built demonstration scenarios:
  A – Clean batch (all steps pass, Release)
  B – Minor deviation (out-of-range parameter, Release with Comments)
  C – Critical hold (mandatory step skipped, Reject / Hold)
"""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.enums import (
    BatchStatus,
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
    Disposition,
    OrderStatus,
    ReviewStatus,
    StepStatus,
)
from ..domain.models import (
    AuditEvent,
    Batch,
    Deviation,
    ParameterRecord,
    ProductionOrder,
    ReviewDecision,
    StepExecution,
)
from ..utils.helpers import now_iso
from ..utils.persistence import reset_all, save_all, upsert
from ..services import audit_service
from ..services.recipe_service import load_seed_recipes, get_recipe
from ..services.order_service import get_all_orders
from ..services.batch_service import create_batch, get_executions_for_batch, update_execution, update_batch, get_batch

_SEED_ORDERS_PATH = Path(__file__).parent / "seed_orders.json"
_PARAM_ENTITY = "parameters"
_DEV_ENTITY = "deviations"


def _load_seed_orders() -> None:
    from ..utils.persistence import load_all, save_all
    from ..domain.models import ProductionOrder
    existing = load_all("orders", ProductionOrder)
    if existing:
        return
    with open(_SEED_ORDERS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    orders = [ProductionOrder.model_validate(r) for r in raw]
    save_all("orders", orders)


def _complete_step(exe: StepExecution, params: dict, operator: str) -> StepExecution:
    exe.status = StepStatus.COMPLETED
    exe.started_at = now_iso()
    exe.completed_at = now_iso()
    exe.operator = operator
    return exe


def _param(exe: StepExecution, name: str, value, unit: str, within_spec: bool, operator: str) -> ParameterRecord:
    return ParameterRecord(
        execution_id=exe.execution_id,
        batch_id=exe.batch_id,
        step_id=exe.step_id,
        name=name,
        value=value,
        unit=unit,
        within_spec=within_spec,
        recorded_by=operator,
    )


def seed_scenario_a() -> Batch:
    """Scenario A: Clean batch – all steps pass, Release."""
    orders = get_all_orders()
    order = next((o for o in orders if o.order_id == "ORD-DEMO-001"), None)
    if not order:
        return None

    batch = create_batch(
        order_id=order.order_id,
        product_code=order.product_code,
        product_name=order.product_name,
        site=order.site,
        quantity=order.quantity,
        unit=order.unit,
        recipe_id="RCP-TABLET-001",
        created_by="mes_operator",
    )

    executions = get_executions_for_batch(batch.batch_id)
    params_all = []

    step_params = {
        "S01": [("operator_id", "OP-001", "", True), ("clearance_result", "Pass", "", True)],
        "S02": [("operator_id", "OP-001", "", True), ("api_weight_kg", 5.002, "kg", True), ("excipient_weight_kg", 10.001, "kg", True)],
        "S03": [("operator_id", "OP-002", "", True), ("mixing_speed_rpm", 300.0, "rpm", True), ("temperature_c", 22.0, "°C", True), ("mix_duration_min", 60.0, "min", True)],
        "S04": [("operator_id", "OP-002", "", True), ("inlet_air_temp_c", 60.0, "°C", True), ("lod_percent", 1.5, "%", True)],
        "S05": [("operator_id", "OP-003", "", True), ("blend_time_min", 30.0, "min", True), ("blend_speed_rpm", 15.0, "rpm", True)],
        "S06": [("operator_id", "OP-003", "", True), ("tablet_weight_mg", 501.0, "mg", True), ("hardness_kp", 10.0, "kP", True), ("yield_kg", 14.2, "kg", True)],
        "S07": [("operator_id", "OP-QC", "", True), ("dissolution_percent", 92.0, "%", True), ("visual_inspection", "Pass", "", True)],
        "S08": [("reviewer_id", "SUP-001", "", True), ("review_result", "Pass", "", True)],
    }

    for exe in executions:
        exe = _complete_step(exe, {}, "OP-001")
        for name, val, unit, ws in step_params.get(exe.step_id, []):
            p = _param(exe, name, val, unit, ws, "OP-001")
            params_all.append(p)
            exe.parameters.append(p)
        update_execution(exe)

    for p in params_all:
        upsert(_PARAM_ENTITY, ParameterRecord, p, "parameter_id")

    b = get_batch(batch.batch_id)
    b.status = BatchStatus.COMPLETED
    b.review_status = ReviewStatus.COMPLETED
    b.disposition = Disposition.RELEASE
    b.reviewed_by = "QA-001"
    b.review_comment = "All parameters within specification. Batch approved for release."
    update_batch(b)

    audit_service.log_event("QA-001", "batch reviewed", "Batch", b.batch_id, new_value=Disposition.RELEASE.value, comment="Scenario A: Clean batch")
    return b


def seed_scenario_b() -> Batch:
    """Scenario B: Minor deviation – one out-of-range value, Release with Comments."""
    orders = get_all_orders()
    order = next((o for o in orders if o.order_id == "ORD-DEMO-002"), None)
    if not order:
        return None

    batch = create_batch(
        order_id=order.order_id,
        product_code=order.product_code,
        product_name=order.product_name,
        site=order.site,
        quantity=order.quantity,
        unit=order.unit,
        recipe_id="RCP-TABLET-001",
        created_by="mes_operator",
    )

    executions = get_executions_for_batch(batch.batch_id)
    params_all = []

    step_params = {
        "S01": [("operator_id", "OP-004", "", True), ("clearance_result", "Pass", "", True)],
        "S02": [("operator_id", "OP-004", "", True), ("api_weight_kg", 5.001, "kg", True), ("excipient_weight_kg", 10.002, "kg", True)],
        # Temperature out of range (26.5°C > 25°C max) → minor deviation
        "S03": [("operator_id", "OP-005", "", True), ("mixing_speed_rpm", 310.0, "rpm", True), ("temperature_c", 26.5, "°C", False), ("mix_duration_min", 60.0, "min", True)],
        "S04": [("operator_id", "OP-005", "", True), ("inlet_air_temp_c", 60.0, "°C", True), ("lod_percent", 1.8, "%", True)],
        "S05": [("operator_id", "OP-006", "", True), ("blend_time_min", 30.0, "min", True), ("blend_speed_rpm", 14.0, "rpm", True)],
        "S06": [("operator_id", "OP-006", "", True), ("tablet_weight_mg", 500.0, "mg", True), ("hardness_kp", 9.5, "kP", True), ("yield_kg", 14.0, "kg", True)],
        "S07": [("operator_id", "OP-QC", "", True), ("dissolution_percent", 85.0, "%", True), ("visual_inspection", "Pass", "", True)],
        "S08": [("reviewer_id", "SUP-002", "", True), ("review_result", "Pass", "", True)],
    }

    for exe in executions:
        exe = _complete_step(exe, {}, "OP-004")
        for name, val, unit, ws in step_params.get(exe.step_id, []):
            p = _param(exe, name, val, unit, ws, "OP-004")
            params_all.append(p)
            exe.parameters.append(p)
        if exe.step_id == "S03":
            exe.status = StepStatus.DEVIATED
        update_execution(exe)

    for p in params_all:
        upsert(_PARAM_ENTITY, ParameterRecord, p, "parameter_id")

    # Create deviation
    dev = Deviation(
        batch_id=batch.batch_id,
        step_id="S03",
        step_name="Granulation – Wet Mix",
        category=DeviationCategory.OUT_OF_RANGE,
        severity=DeviationSeverity.MAJOR,
        description="Mixing temperature 26.5°C exceeded maximum limit of 25°C. Excursion duration: ~5 min.",
        detected_by="OP-005",
        status=DeviationStatus.APPROVED_WITH_JUSTIFICATION,
        justification="Temperature excursion was brief (5 min) and product quality was confirmed by IPC testing. No impact on product quality.",
        corrective_action="Recalibrate temperature probe; retrain operator on monitoring frequency.",
        disposition="Acceptable with justification",
        closed_at=now_iso(),
        closed_by="QA-002",
    )
    upsert(_DEV_ENTITY, Deviation, dev, "deviation_id")

    b = get_batch(batch.batch_id)
    b.status = BatchStatus.COMPLETED
    b.deviation_count = 1
    b.review_status = ReviewStatus.COMPLETED
    b.disposition = Disposition.RELEASE_WITH_COMMENTS
    b.reviewed_by = "QA-002"
    b.review_comment = "Minor temperature excursion in S03 justified. Batch released with comments."
    update_batch(b)

    audit_service.log_event("QA-002", "batch reviewed", "Batch", b.batch_id, new_value=Disposition.RELEASE_WITH_COMMENTS.value, comment="Scenario B: Minor deviation")
    return b


def seed_scenario_c() -> Batch:
    """Scenario C: Critical hold – mandatory step skipped, Reject / Hold."""
    orders = get_all_orders()
    order = next((o for o in orders if o.order_id == "ORD-DEMO-003"), None)
    if not order:
        return None

    batch = create_batch(
        order_id=order.order_id,
        product_code=order.product_code,
        product_name=order.product_name,
        site=order.site,
        quantity=order.quantity,
        unit=order.unit,
        recipe_id="RCP-INJECT-001",
        created_by="mes_operator",
    )

    executions = get_executions_for_batch(batch.batch_id)
    params_all = []

    step_params = {
        "I01": [("operator_id", "OP-007", "", True), ("clearance_result", "Pass", "", True)],
        "I02": [("operator_id", "OP-007", "", True), ("api_weight_g", 100.0, "g", True)],
        "I03": [("operator_id", "OP-008", "", True), ("ph_value", 7.0, "pH", True), ("temperature_c", 20.0, "°C", True), ("clarity_check", "Pass", "", True)],
        # I04 Sterile Filtration – SKIPPED (critical deviation)
        "I04": [],
        "I05": [("operator_id", "OP-008", "", True), ("fill_volume_ml", 10.0, "mL", True), ("yield_vials", 950.0, "vials", True)],
        # I06 Visual Inspection – FAILED
        "I06": [("operator_id", "OP-QC", "", True), ("inspection_result", "Fail", "", False), ("reject_rate_percent", 1.2, "%", False)],
        "I07": [],
    }

    for exe in executions:
        if exe.step_id == "I04":
            exe.status = StepStatus.SKIPPED
            exe.comments = "Step skipped due to time pressure – NOT ACCEPTABLE"
            update_execution(exe)
            continue
        if exe.step_id == "I07":
            exe.status = StepStatus.NOT_STARTED
            update_execution(exe)
            continue

        exe = _complete_step(exe, {}, "OP-007")
        for name, val, unit, ws in step_params.get(exe.step_id, []):
            p = _param(exe, name, val, unit, ws, "OP-007")
            params_all.append(p)
            exe.parameters.append(p)
        if exe.step_id == "I06":
            exe.status = StepStatus.DEVIATED
        update_execution(exe)

    for p in params_all:
        upsert(_PARAM_ENTITY, ParameterRecord, p, "parameter_id")

    # Critical deviation: skipped sterile filtration
    dev1 = Deviation(
        batch_id=batch.batch_id,
        step_id="I04",
        step_name="Sterile Filtration",
        category=DeviationCategory.SKIPPED_STEP,
        severity=DeviationSeverity.CRITICAL,
        description="Mandatory sterile filtration step was skipped. Product sterility cannot be assured.",
        detected_by="system",
        status=DeviationStatus.OPEN,
    )
    upsert(_DEV_ENTITY, Deviation, dev1, "deviation_id")

    # Major deviation: failed visual inspection
    dev2 = Deviation(
        batch_id=batch.batch_id,
        step_id="I06",
        step_name="Visual Inspection",
        category=DeviationCategory.FAILED_INSPECTION,
        severity=DeviationSeverity.MAJOR,
        description="Visual inspection failed. Reject rate 1.2% exceeds 0.5% limit. Particulate contamination suspected.",
        detected_by="OP-QC",
        status=DeviationStatus.ESCALATED,
    )
    upsert(_DEV_ENTITY, Deviation, dev2, "deviation_id")

    b = get_batch(batch.batch_id)
    b.status = BatchStatus.ON_HOLD
    b.deviation_count = 2
    b.review_status = ReviewStatus.IN_REVIEW
    b.disposition = Disposition.REJECT_HOLD
    b.reviewed_by = "QA-003"
    b.review_comment = "Critical deviation: sterile filtration skipped. Batch placed on hold pending investigation."
    update_batch(b)

    audit_service.log_event("QA-003", "batch reviewed", "Batch", b.batch_id, new_value=Disposition.REJECT_HOLD.value, comment="Scenario C: Critical hold")
    return b


def load_all_demo_scenarios() -> dict:
    """Load seed data and all three demo scenarios. Idempotent."""
    load_seed_recipes()
    _load_seed_orders()

    from ..utils.persistence import load_all
    from ..domain.models import Batch
    existing_batches = load_all("batches", Batch)
    existing_orders = {b.order_id for b in existing_batches}

    results = {}
    if "ORD-DEMO-001" not in existing_orders:
        results["scenario_a"] = seed_scenario_a()
    if "ORD-DEMO-002" not in existing_orders:
        results["scenario_b"] = seed_scenario_b()
    if "ORD-DEMO-003" not in existing_orders:
        results["scenario_c"] = seed_scenario_c()
    return results
