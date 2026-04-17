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
    """Update ERP order status to 'in_production' (ERP canonical value)."""
    ok = _erp.update_order_status(pharma_order_id, "in_production")
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
    Correct 4-step MES/PCS integration flow:
    1. Create a dedicated MES machine for this batch → get mes_machine_id (DB primary key).
    2. Create MES work order linked to that machine → get mes_wo_id (DB primary key).
    3. Register the PCS machine using the same mes_machine_id so cross-validation passes.
    4. Start the PCS machine passing mes_wo_id as work_order_id.
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

    # Step 1 – Create a dedicated MES machine for this batch.
    # The DB primary key returned here is used as the PCS machine_id so that
    # PCS cross-validation (work_order.machine_id == pcs_machine_id) passes.
    mes_machine = _mes.create_machine(
        machine_code=f"PHARMA-{batch_id}",
        name=f"Pharma Batch Machine {batch_id}",
        machine_type="pharma_batch",
    )
    mes_machine_id: Optional[int] = mes_machine["id"] if mes_machine else None
    results["mes_machine"] = mes_machine
    results["mes_machine_id"] = mes_machine_id

    # Step 2 – Create MES work order linked to the new machine.
    mes_wo = _mes.create_work_order(
        batch_id=batch_id,
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        production_plan_id=plan_id,
        machine_id=mes_machine_id,
    )
    mes_wo_id: Optional[int] = mes_wo["id"] if mes_wo else None
    results["mes_work_order"] = mes_wo
    results["mes_work_order_id"] = mes_wo_id

    # Steps 3 & 4 – Register PCS machine (same integer id) then start it.
    if mes_machine_id and mes_wo_id:
        _pcs.ensure_machine(mes_machine_id)
        started = _pcs.start_machine(mes_machine_id, work_order_id=mes_wo_id)
        results["pcs_machine_started"] = mes_machine_id if started else None
    else:
        logger.warning(
            "on_batch_created: skipping PCS start – mes_machine_id=%s mes_wo_id=%s",
            mes_machine_id, mes_wo_id,
        )
        results["pcs_machine_started"] = None

    logger.info(
        "on_batch_created: %s → MES machine=%s WO=%s PCS started=%s",
        batch_id, mes_machine_id, mes_wo_id, results.get("pcs_machine_started"),
    )
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


## ── Batch Completed ──────────────────────────────────────────────────────
def on_batch_completed(batch_id: str, product_code: str, quantity: float) -> Dict[str, Any]:
    """
    When a batch is completed:
    - Update MES work order to 'completed'.
    - Stop the assigned PCS machine (best-effort).
      The MES work order stores the machine_id that was used at creation time;
      that same integer is the PCS machine_id (they were kept in sync by on_batch_created).
    """
    results: Dict[str, Any] = {}

    ok_mes = _mes.update_work_order_status(batch_id, "completed")
    results["mes_status_updated"] = ok_mes

    # Stop PCS machine — the MES work order machine_id IS the PCS machine_id
    mes_wo = _mes.get_work_order_by_number(batch_id)
    pcs_machine_id = mes_wo.get("machine_id") if mes_wo else None
    if pcs_machine_id:
        stopped = _pcs.stop_machine(pcs_machine_id)
        results["pcs_machine_stopped"] = pcs_machine_id if stopped else None
        logger.info("on_batch_completed: %s → PCS machine %s stopped=%s", batch_id, pcs_machine_id, stopped)
    else:
        results["pcs_machine_stopped"] = None
        logger.warning("on_batch_completed: no machine_id found for batch %s", batch_id)

    return results


# ── Batch Released ─────────────────────────────────────────────────────────
def on_batch_released(
    batch_id: str,
    product_code: str,
    quantity: float,
    pharma_order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    When a batch is released (QA approved):
    - Update ERP product stock (add released quantity).
    - Update ERP order status to 'completed'.
    The ERP order was created with the pharma *order_id* as its order_number,
    not the batch_id, so we must look it up by order_id when available.
    """
    results: Dict[str, Any] = {}

    ok_stock = _erp.update_product_stock(product_code, quantity)
    results["erp_stock_updated"] = ok_stock

    # Prefer the pharma order_id for ERP lookup; fall back to batch_id
    erp_order_number = pharma_order_id or batch_id
    ok_order = _erp.update_order_status(erp_order_number, "completed")
    results["erp_order_completed"] = ok_order

    logger.info(
        "on_batch_released: batch=%s order=%s product=%s qty=%.2f",
        batch_id, erp_order_number, product_code, quantity,
    )
    return results


## ── Batch Rejected ──────────────────────────────────────────────────────
def on_batch_rejected(
    batch_id: str,
    reason: str,
    pharma_order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update MES work order to 'cancelled', stop PCS machine, and cancel ERP order.

    Note: MES valid statuses are planned/scheduled/in_progress/completed/cancelled.
    'on_hold' is not a valid MES status; 'cancelled' is the correct terminal state.
    """
    ok_mes = _mes.update_work_order_status(batch_id, "cancelled")
    erp_order_number = pharma_order_id or batch_id
    ok_erp = _erp.update_order_status(erp_order_number, "cancelled")

    # Stop PCS machine — the MES work order machine_id IS the PCS machine_id
    mes_wo = _mes.get_work_order_by_number(batch_id)
    pcs_machine_id = mes_wo.get("machine_id") if mes_wo else None
    pcs_stopped = False
    if pcs_machine_id:
        pcs_stopped = _pcs.stop_machine(pcs_machine_id)

    logger.info(
        "on_batch_rejected: batch=%s order=%s reason=%s pcs_machine=%s stopped=%s",
        batch_id, erp_order_number, reason, pcs_machine_id, pcs_stopped,
    )
    return {"mes_cancelled": ok_mes, "erp_cancelled": ok_erp, "pcs_machine_stopped": pcs_machine_id if pcs_stopped else None}


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
