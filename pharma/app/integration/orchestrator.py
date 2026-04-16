"""
Integration Orchestrator
High-level functions that coordinate ERP + MES + PCS calls for each
pharma lifecycle event. Called by pharma services; all calls are
best-effort (failures are logged, not raised) unless STRICT_MODE is set.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .erp_client import ERPClient
from .mes_client import MESClient
from .pcs_client import PCSClient

logger = logging.getLogger("pharma.integration.orchestrator")

# Singletons – created once per process
_erp = ERPClient()
_mes = MESClient()
_pcs = PCSClient()


# ── Health ─────────────────────────────────────────────────────────────────
def get_system_health() -> Dict[str, Dict]:
    """Return online/offline status for all three upstream systems."""
    return {
        "ERP": _erp.health(),
        "MES": _mes.health(),
        "PCS": _pcs.health(),
    }


# ── Order Created ──────────────────────────────────────────────────────────
def on_order_created(
    pharma_order_id: str,
    product_code: str,
    product_name: str,
    quantity: float,
    due_date: str,
    site: str,
) -> Dict[str, Any]:
    """
    Called when a pharma production order is created.
    1. Ensure ERP product exists.
    2. Create ERP production order.
    3. Create ERP production plan.
    """
    results: Dict[str, Any] = {}

    # ERP: ensure product
    erp_product = _erp.ensure_product(product_code, product_name)
    results["erp_product"] = erp_product

    # ERP: create production order
    erp_order = _erp.create_production_order(
        pharma_order_id=pharma_order_id,
        product_code=product_code,
        product_name=product_name,
        quantity=quantity,
        due_date=due_date,
        site=site,
    )
    results["erp_order"] = erp_order

    # ERP: create production plan
    if erp_order:
        erp_plan = _erp.create_production_plan(
            plan_number=f"PP-{pharma_order_id}",
            order_id=erp_order.get("id"),
        )
        results["erp_plan"] = erp_plan

    logger.info("on_order_created: %s → ERP order=%s", pharma_order_id, erp_order)
    return results


# ── Order Sent to MES ──────────────────────────────────────────────────────
def on_order_sent_to_mes(pharma_order_id: str) -> Dict[str, Any]:
    """Update ERP order status to 'in_progress'."""
    ok = _erp.update_order_status(pharma_order_id, "in_progress")
    return {"erp_status_updated": ok}


# ── Batch Instantiated ─────────────────────────────────────────────────────
def on_batch_created(
    batch_id: str,
    pharma_order_id: str,
    product_code: str,
    product_name: str,
    quantity: float,
    recipe_steps: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Called when a pharma batch is instantiated.
    1. Look up ERP product id.
    2. Create MES production plan linked to ERP order.
    3. Create MES work order for the batch.
    4. Allocate materials in MES.
    5. Assign first available machine (best-effort).
    """
    results: Dict[str, Any] = {}

    # ERP product id
    erp_product = _erp.get_product_by_code(product_code)
    if not erp_product:
        erp_product = _erp.ensure_product(product_code, product_name)
    product_id = erp_product["id"] if erp_product else 1  # fallback

    # ERP order id
    erp_order = _erp.get_order_by_number(pharma_order_id)
    erp_order_id = erp_order["id"] if erp_order else None

    # MES production plan
    mes_plan = _mes.create_production_plan(
        plan_number=f"PP-{batch_id}",
        order_id=erp_order_id,
    )
    plan_id = mes_plan["id"] if mes_plan else 1  # fallback
    results["mes_plan"] = mes_plan

    # Pick first available machine
    available_machines = _mes.get_available_machines()
    machine_id = available_machines[0]["id"] if available_machines else None
    results["assigned_machine_id"] = machine_id

    # MES work order
    mes_wo = _mes.create_work_order(
        batch_id=batch_id,
        product_id=product_id,
        quantity=quantity,
        production_plan_id=plan_id,
        machine_id=machine_id,
    )
    results["mes_work_order"] = mes_wo

    # Start machine if assigned
    if machine_id:
        pcs_machine_ids = [m.get("id") for m in _pcs.get_all_machines_status() if m.get("id")]
        if pcs_machine_ids:
            _pcs.start_machine(pcs_machine_ids[0])
            results["pcs_machine_started"] = pcs_machine_ids[0]

    logger.info("on_batch_created: %s → MES WO=%s machine=%s", batch_id, mes_wo, machine_id)
    return results


# ── Step Started ───────────────────────────────────────────────────────────
def on_step_started(batch_id: str, step_name: str, operator: str) -> Dict[str, Any]:
    """Update MES work order to in_progress when first step starts."""
    ok = _mes.update_work_order_status(batch_id, "in_progress")
    return {"mes_status_updated": ok}


# ── Parameter Captured ─────────────────────────────────────────────────────
def on_parameter_captured(
    batch_id: str,
    step_name: str,
    parameter_name: str,
    value: Any,
    unit: str,
    within_spec: bool,
    min_value: Optional[float],
    max_value: Optional[float],
) -> Dict[str, Any]:
    """
    Push a quality check to MES for every captured parameter.
    Also attempt to read live PCS sensor data for the same parameter name.
    """
    results: Dict[str, Any] = {}

    # Convert value to float if possible
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = 0.0

    # MES quality check
    qc = _mes.create_quality_check(
        work_order_number=batch_id,
        check_type="process_parameter",
        parameter_name=parameter_name,
        actual_value=numeric_value,
        min_value=min_value,
        max_value=max_value,
        passed=within_spec,
        notes=f"Step: {step_name}",
    )
    results["mes_quality_check"] = qc

    # PCS: try to read matching sensor for reference
    pcs_machines = _pcs.get_all_machines_status()
    if pcs_machines:
        machine_id = pcs_machines[0].get("id")
        if machine_id:
            sensor_data = _pcs.get_latest_sensor_data(machine_id)
            results["pcs_sensor_snapshot"] = sensor_data

    return results


# ── Step Completed ─────────────────────────────────────────────────────────
def on_step_completed(batch_id: str, step_name: str, operator: str) -> Dict[str, Any]:
    """Increment MES production count on step completion."""
    ok = _mes.increment_production_count(batch_id, good=1)
    return {"mes_count_incremented": ok}


# ── Deviation Opened ───────────────────────────────────────────────────────
def on_deviation_opened(
    batch_id: str,
    step_name: str,
    description: str,
    severity: str,
) -> Dict[str, Any]:
    """
    When a deviation is opened:
    - Increment MES reject count.
    - Pull active PCS alarms for context.
    """
    results: Dict[str, Any] = {}
    _mes.increment_production_count(batch_id, reject=1)
    results["mes_reject_incremented"] = True

    active_alarms = _pcs.get_active_alarms()
    results["pcs_active_alarms"] = active_alarms
    if active_alarms:
        logger.warning(
            "Deviation on batch %s step '%s' – %d active PCS alarm(s) at time of event.",
            batch_id, step_name, len(active_alarms),
        )
    return results


# ── Batch Completed ────────────────────────────────────────────────────────
def on_batch_completed(batch_id: str, product_code: str, quantity: float) -> Dict[str, Any]:
    """
    When a batch is completed:
    - Update MES work order to 'completed'.
    - Stop the assigned machine (best-effort).
    - Update ERP product stock.
    """
    results: Dict[str, Any] = {}

    ok_mes = _mes.update_work_order_status(batch_id, "completed")
    results["mes_status_updated"] = ok_mes

    # Stop PCS machine
    pcs_machines = _pcs.get_all_machines_status()
    if pcs_machines:
        machine_id = pcs_machines[0].get("id")
        if machine_id:
            _pcs.stop_machine(machine_id)
            results["pcs_machine_stopped"] = machine_id

    return results


# ── Batch Released ─────────────────────────────────────────────────────────
def on_batch_released(batch_id: str, product_code: str, quantity: float) -> Dict[str, Any]:
    """
    When a batch is released (QA approved):
    - Update ERP product stock (add released quantity).
    - Update ERP order status to 'completed'.
    """
    results: Dict[str, Any] = {}

    ok_stock = _erp.update_product_stock(product_code, quantity)
    results["erp_stock_updated"] = ok_stock

    ok_order = _erp.update_order_status(batch_id, "completed")
    results["erp_order_completed"] = ok_order

    logger.info("on_batch_released: %s product=%s qty=%.2f", batch_id, product_code, quantity)
    return results


# ── Batch Rejected ─────────────────────────────────────────────────────────
def on_batch_rejected(batch_id: str, reason: str) -> Dict[str, Any]:
    """Update MES work order to on_hold and ERP order to cancelled."""
    ok_mes = _mes.update_work_order_status(batch_id, "on_hold")
    ok_erp = _erp.update_order_status(batch_id, "cancelled")
    return {"mes_on_hold": ok_mes, "erp_cancelled": ok_erp}


# ── Live Data Pulls ────────────────────────────────────────────────────────
def get_live_machine_data() -> Dict[str, Any]:
    """Pull live PCS sensor and parameter data for the dashboard."""
    machines = _pcs.get_all_machines_status()
    result = {"machines": []}
    for m in machines:
        mid = m.get("id")
        if not mid:
            continue
        sensors = _pcs.get_latest_sensor_data(mid)
        params = _pcs.get_machine_parameters(mid)
        alarms = _pcs.get_alarms_for_machine(mid)
        state = _pcs.get_machine_state(mid)
        result["machines"].append({
            "machine": m,
            "sensors": sensors,
            "parameters": params,
            "alarms": alarms,
            "state": state,
        })
    return result


def get_mes_production_summary(batch_id: str) -> Optional[Dict]:
    """Pull MES production summary for a batch."""
    return _mes.get_production_summary(batch_id)


def get_mes_quality_summary(batch_id: str) -> Optional[Dict]:
    """Pull MES quality summary for a batch."""
    return _mes.get_quality_summary(batch_id)


def get_erp_inventory_snapshot() -> List[Dict]:
    """Pull current ERP material stock levels."""
    return _erp.get_materials()


def get_erp_products() -> List[Dict]:
    """Pull ERP product catalogue."""
    return _erp.get_products()
