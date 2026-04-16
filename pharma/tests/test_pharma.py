"""
Unit tests for Pharma Batch Execution Simulator domain logic, services,
and integration layer (offline / standalone mode).
"""

import os
import tempfile
import pytest

from pharma.app.domain.enums import DeviationSeverity, Disposition, StepStatus
from pharma.app.domain.models import ParameterSpec
from pharma.app.domain.rules import validate_parameter
from pharma.app.services import batch_service, execution_service, order_service, recipe_service, review_service


@pytest.fixture(autouse=True)
def setup_teardown():
    """Use a temporary directory for data files during tests."""
    temp_dir = tempfile.TemporaryDirectory()
    os.environ["PHARMA_DATA_DIR"] = temp_dir.name

    from pharma.app.utils.persistence import reset_all
    reset_all()
    recipe_service.load_seed_recipes()

    yield

    temp_dir.cleanup()
    os.environ.pop("PHARMA_DATA_DIR", None)


# ── Domain rules ────────────────────────────────────────────────────────────

def test_validate_parameter_numeric():
    spec = ParameterSpec(name="temp", unit="C", data_type="float", min_value=18, max_value=25)

    within, msg, val = validate_parameter(spec, "20.5")
    assert within is True
    assert val == 20.5

    within, msg, val = validate_parameter(spec, "26.0")
    assert within is False
    assert "above maximum" in msg

    within, msg, val = validate_parameter(spec, "not_a_number")
    assert within is False


def test_validate_parameter_boolean():
    spec_bool = ParameterSpec(name="visual", unit="", data_type="boolean", allowed_values=["Pass", "Fail"])

    within, msg, val = validate_parameter(spec_bool, "Pass")
    assert within is True

    within, msg, val = validate_parameter(spec_bool, "Fail")
    assert within is True

    within, msg, val = validate_parameter(spec_bool, "Maybe")
    assert within is False


# ── Order → Batch flow ──────────────────────────────────────────────────────

def test_order_to_batch_flow():
    order = order_service.create_order(
        product_code="TAB-500MG",
        product_name="Metformin Tablet 500mg",
        quantity=15.0,
        unit="kg",
        due_date="2026-05-01",
        site="Site A",
    )
    assert order.order_id.startswith("ORD-")

    order_service.send_to_mes(order.order_id)
    updated_order = order_service.get_order(order.order_id)
    assert updated_order.status.value == "Sent to MES"

    batch = batch_service.create_batch(
        order_id=order.order_id,
        product_code=order.product_code,
        product_name=order.product_name,
        site=order.site,
        quantity=order.quantity,
        unit=order.unit,
        recipe_id="RCP-TABLET-001",
    )
    assert batch.batch_id.startswith("BAT-")

    order_service.mark_in_execution(order.order_id, batch.batch_id)
    final_order = order_service.get_order(order.order_id)
    assert final_order.status.value == "In Execution"
    assert final_order.batch_id_ref == batch.batch_id


# ── Execution and review ────────────────────────────────────────────────────

def test_execution_and_review():
    order = order_service.create_order("TAB-500MG", "Metformin", 15.0, "kg", "2026-05-01", "Site A")
    batch = batch_service.create_batch(
        order.order_id, order.product_code, order.product_name,
        order.site, order.quantity, order.unit, "RCP-TABLET-001",
    )

    execs = batch_service.get_executions_for_batch(batch.batch_id)
    assert len(execs) == 8
    assert execs[0].status == StepStatus.READY

    # Start and complete step 1
    exe1 = execution_service.start_step(batch.batch_id, execs[0].step_id, "OP-001")
    assert exe1.status == StepStatus.IN_PROGRESS

    execution_service.capture_parameters(
        batch.batch_id, execs[0].step_id,
        {"operator_id": "OP-001", "clearance_result": "Pass"},
        "OP-001", "RCP-TABLET-001",
    )
    execution_service.complete_step(batch.batch_id, execs[0].step_id, "OP-001")

    # Skip remaining steps (all required → critical deviations)
    for exe in execs[1:]:
        execution_service.skip_step(batch.batch_id, exe.step_id, "OP-001", "Testing", step_required=True)

    decision = review_service.compute_review(batch.batch_id)
    assert decision.disposition == Disposition.REJECT_HOLD
    assert (
        "critical deviation(s) remain open" in decision.comment
        or "mandatory step(s) not completed" in decision.comment
    )


# ── Integration layer – offline mode ───────────────────────────────────────

def test_integration_config_loads():
    """Integration config should load without raising even when systems are offline."""
    from pharma.app.integration.config import ERP_BASE_URL, MES_BASE_URL, PCS_BASE_URL
    assert ERP_BASE_URL.startswith("http")
    assert MES_BASE_URL.startswith("http")
    assert PCS_BASE_URL.startswith("http")


def test_integration_health_offline():
    """Health check returns offline status gracefully when systems are not running."""
    from pharma.app.integration.orchestrator import get_system_health
    health = get_system_health()
    assert "ERP" in health
    assert "MES" in health
    assert "PCS" in health
    # In test environment systems are not running – online should be False
    for key in ("ERP", "MES", "PCS"):
        assert isinstance(health[key]["online"], bool)


def test_integration_hooks_do_not_raise_when_offline():
    """
    All integration hooks must be non-fatal: even when ERP/MES/PCS are offline,
    the pharma services must complete their local operations successfully.
    """
    order = order_service.create_order(
        product_code="TAB-500MG",
        product_name="Metformin Tablet 500mg",
        quantity=10.0,
        unit="kg",
        due_date="2026-06-01",
        site="Site B",
    )
    # send_to_mes fires on_order_sent_to_mes → must not raise
    result = order_service.send_to_mes(order.order_id)
    assert result is not None

    # create_batch fires on_batch_created → must not raise
    batch = batch_service.create_batch(
        order_id=order.order_id,
        product_code=order.product_code,
        product_name=order.product_name,
        site=order.site,
        quantity=order.quantity,
        unit=order.unit,
        recipe_id="RCP-TABLET-001",
    )
    assert batch is not None

    # start_step fires on_step_started → must not raise
    execs = batch_service.get_executions_for_batch(batch.batch_id)
    exe = execution_service.start_step(batch.batch_id, execs[0].step_id, "OP-TEST")
    assert exe is not None

    # capture_parameters fires on_parameter_captured → must not raise
    records, devs = execution_service.capture_parameters(
        batch.batch_id, execs[0].step_id,
        {"operator_id": "OP-TEST", "clearance_result": "Pass"},
        "OP-TEST", "RCP-TABLET-001",
    )
    assert isinstance(records, list)

    # complete_step fires on_step_completed → must not raise
    exe = execution_service.complete_step(batch.batch_id, execs[0].step_id, "OP-TEST")
    assert exe is not None


def test_erp_client_offline():
    """ERP client is_online() returns False when ERP is not running."""
    from pharma.app.integration.erp_client import ERPClient
    erp = ERPClient()
    assert erp.is_online() is False
    # get_products returns empty list, not an exception
    products = erp.get_products()
    assert isinstance(products, list)


def test_mes_client_offline():
    """MES client is_online() returns False when MES is not running."""
    from pharma.app.integration.mes_client import MESClient
    mes = MESClient()
    assert mes.is_online() is False
    work_orders = mes.get_work_orders()
    assert isinstance(work_orders, list)


def test_pcs_client_offline():
    """PCS client is_online() returns False when PCS is not running."""
    from pharma.app.integration.pcs_client import PCSClient
    pcs = PCSClient()
    assert pcs.is_online() is False
    alarms = pcs.get_active_alarms()
    assert isinstance(alarms, list)
