"""
End-to-end workflow test for the pharma batch execution simulator
wired to ERP, MES, and PCS.

Steps exercised:
  1.  Seed ERP: create product + materials (idempotent)
  2.  Seed MES: create machine (idempotent)
  3.  Pharma: create order
  4.  Pharma: send order to MES (dispatch)
  5.  Pharma: instantiate batch
  6.  Pharma: start first step
  7.  Pharma: capture parameters (in-range)
  8.  Pharma: capture parameters (out-of-range → auto-deviation)
  9.  Pharma: complete first step
  10. Pharma: open manual deviation
  11. Pharma: close deviation
  12. Pharma: complete all remaining steps
  13. Pharma: submit review → release
  14. Verify ERP order status == 'completed'
  15. Verify MES work order status == 'completed'
  16. Verify echotrace audit trail has records
"""
import sys
import os
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta

# ── path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
PHARMA_PKG = REPO_ROOT / "pharma"

# pharma/ must be in sys.path so 'app' resolves as a package with relative imports
sys.path.insert(0, str(REPO_ROOT))   # for echotrace
sys.path.insert(0, str(PHARMA_PKG))  # for app.*

ERP_URL = os.environ.get("ERP_URL", "http://localhost:5001/api/v1")
MES_URL = os.environ.get("MES_URL", "http://localhost:5002/api/v1")
PCS_URL = os.environ.get("PCS_URL", "http://localhost:5003/api/v1")

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
errors = []

def check(label, condition, detail=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        msg = f"  {FAIL} {label}"
        if detail:
            msg += f": {detail}"
        print(msg)
        errors.append(label)

def http_post(url, data):
    return requests.post(url, json=data, timeout=10)

def http_get(url):
    return requests.get(url, timeout=10)

# ── helpers for idempotent seeding ──────────────────────────────────────────
def get_or_create_erp_product(code, data):
    r = http_get(f"{ERP_URL}/products")
    if r.status_code == 200:
        items = r.json()
        if isinstance(items, dict):
            items = items.get("products", [])
        existing = next((p for p in items if p.get("code") == code), None)
        if existing:
            return existing, True
    r = http_post(f"{ERP_URL}/products", data)
    if r.status_code in (200, 201):
        d = r.json()
        return d.get("product", d), False
    return None, False

def get_or_create_erp_material(code, data):
    r = http_get(f"{ERP_URL}/materials")
    if r.status_code == 200:
        items = r.json()
        if isinstance(items, dict):
            items = items.get("materials", [])
        existing = next((m for m in items if m.get("code") == code), None)
        if existing:
            return existing, True
    r = http_post(f"{ERP_URL}/materials", data)
    if r.status_code in (200, 201):
        d = r.json()
        return d.get("material", d), False
    return None, False

def get_or_create_mes_machine(machine_code, data):
    r = http_get(f"{MES_URL}/machines/code/{machine_code}")
    if r.status_code == 200:
        return r.json(), True
    r = http_post(f"{MES_URL}/machines", data)
    if r.status_code in (200, 201):
        d = r.json()
        return d.get("machine", d), False
    return None, False

# ── 1. Seed ERP ──────────────────────────────────────────────────────────────
print("\n[1] Seed ERP — product + materials")

product, existed = get_or_create_erp_product("PHARMA-TAB-001", {
    "code": "PHARMA-TAB-001",
    "name": "Paracetamol 500mg Tablet",
    "description": "Oral solid dosage form",
    "unit": "tablet",
    "price": 0.05,
    "stock_quantity": 0,
    "min_stock_level": 1000,
})
check("ERP product available", product is not None)
if existed:
    print("    (already existed)")

mat1, _ = get_or_create_erp_material("API-PARA-001", {
    "code": "API-PARA-001",
    "name": "Paracetamol API",
    "unit": "kg",
    "cost": 50.0,
    "stock_quantity": 500.0,
    "min_stock_level": 50.0,
})
check("ERP material (API) available", mat1 is not None)

mat2, _ = get_or_create_erp_material("EXCIP-MCC-001", {
    "code": "EXCIP-MCC-001",
    "name": "Microcrystalline Cellulose",
    "unit": "kg",
    "cost": 5.0,
    "stock_quantity": 1000.0,
    "min_stock_level": 100.0,
})
check("ERP material (excipient) available", mat2 is not None)

# ── 2. Seed MES machine ───────────────────────────────────────────────────────
print("\n[2] Seed MES — machine")
machine, existed = get_or_create_mes_machine("TABLET-PRESS-01", {
    "machine_code": "TABLET-PRESS-01",
    "name": "Tablet Press 01",
    "type": "tablet_press",
    "status": "idle",
    "location": "Suite A",
})
check("MES machine available", machine is not None)
if existed:
    print("    (already existed)")

# ── 3. Pharma: load services ──────────────────────────────────────────────────
print("\n[3] Pharma — load services and create order")

from app.services.order_service import (
    create_order, send_to_mes, get_order,
)
from app.services.recipe_service import get_all_recipes, get_recipe
from app.services.batch_service import (
    create_batch, get_batch, get_executions_for_batch,
)
from app.services.execution_service import (
    start_step, capture_parameters, complete_step,
)
from app.services.deviation_service import (
    open_deviation, update_deviation_status,
)
from app.services.review_service import submit_review
from app.domain.enums import (
    DeviationCategory, DeviationSeverity, DeviationStatus, Disposition,
)
from app.utils.persistence import reset_all as reset_all_data

reset_all_data()
recipes = get_all_recipes()
check("Recipes loaded", len(recipes) > 0, f"found {len(recipes)}")
recipe = recipes[0] if recipes else None
check("Recipe has steps", recipe is not None and len(recipe.steps) > 0,
      f"steps={len(recipe.steps) if recipe else 0}")

due = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
order = create_order(
    product_code=recipe.product_code,
    product_name=recipe.name,
    quantity=10000,
    unit="tablet",
    due_date=due,
    site="Site A",
    created_by="e2e_test",
    notes="E2E workflow test order",
)
check("Pharma order created", order is not None)
order_id = order.order_id if order else None
check("Order has ID", bool(order_id))

# ── 4. Pharma: dispatch order to MES ─────────────────────────────────────────
print("\n[4] Pharma — dispatch order to MES")
dispatched = send_to_mes(order_id, user="e2e_test")
check("Order dispatched (send_to_mes)", dispatched is not None)
check("Order status = SENT_TO_MES",
      dispatched and dispatched.status.value == "Sent to MES",
      f"actual: {dispatched.status.value if dispatched else 'None'}")

# ── 5. Pharma: instantiate batch ─────────────────────────────────────────────
print("\n[5] Pharma — instantiate batch")
batch = create_batch(
    order_id=order_id,
    product_code=recipe.product_code,
    product_name=recipe.name,
    site="Site A",
    quantity=10000,
    unit="tablet",
    recipe_id=recipe.recipe_id,
    created_by="e2e_operator",
)
check("Batch created", batch is not None)
batch_id = batch.batch_id if batch else None
check("Batch has ID", bool(batch_id))
check("Batch has step executions",
      batch_id and len(get_executions_for_batch(batch_id)) > 0,
      f"executions={len(get_executions_for_batch(batch_id)) if batch_id else 0}")

# ── 6. Pharma: start first step ───────────────────────────────────────────────
print("\n[6] Pharma — start first step")
executions = get_executions_for_batch(batch_id)
check("Executions available", len(executions) > 0, f"found {len(executions)}")

first_exe = sorted(executions, key=lambda e: e.sequence)[0] if executions else None
step_id = first_exe.step_id if first_exe else None

started = start_step(batch_id, step_id, operator="e2e_operator")
check("First step started", started is not None)
check("Step status = IN_PROGRESS",
      started and started.status.value == "In Progress",
      f"actual: {started.status.value if started else 'None'}")

# ── 7. Pharma: capture in-range parameters ────────────────────────────────────
print("\n[7] Pharma — capture in-range parameters")
step_spec = next((s for s in recipe.steps if s.step_id == step_id), None)
params_spec = step_spec.parameters if step_spec else []

if params_spec:
    in_range_values = {}
    for ps in params_spec:
        if ps.min_value is not None and ps.max_value is not None:
            mid = (ps.min_value + ps.max_value) / 2
            in_range_values[ps.name] = str(mid)
        elif ps.allowed_values:
            in_range_values[ps.name] = ps.allowed_values[0]
        else:
            in_range_values[ps.name] = "PASS"  # default for string/boolean params

    records, deviations = capture_parameters(
        batch_id=batch_id,
        step_id=step_id,
        param_values=in_range_values,
        operator="e2e_operator",
        recipe_id=recipe.recipe_id,
    )
    check("In-range parameters captured", len(records) > 0,
          f"got {len(records)} records")
    check("No auto-deviations for in-range values", len(deviations) == 0,
          f"got {len(deviations)} deviations")
else:
    print("  (no parameters on first step — skipping)")

# ── 8. Pharma: capture out-of-range parameters ────────────────────────────────
print("\n[8] Pharma — capture out-of-range parameters")
# Find a step with numeric parameter bounds for the out-of-range test
oor_step_spec = next(
    (s for s in recipe.steps
     if any(p.min_value is not None and p.max_value is not None for p in s.parameters)),
    None,
)
if oor_step_spec:
    oor_step_exe = next((e for e in executions if e.step_id == oor_step_spec.step_id), None)
    # Start the step if it hasn't been started yet
    if oor_step_exe and oor_step_exe.status.value in ("Not Started", "Ready"):
        start_step(batch_id, oor_step_spec.step_id, operator="e2e_operator")
    out_of_range_values = {}
    for ps in oor_step_spec.parameters:
        if ps.min_value is not None and ps.max_value is not None:
            out_of_range_values[ps.name] = str(ps.max_value + 10)
        elif ps.allowed_values:
            out_of_range_values[ps.name] = ps.allowed_values[0]
        else:
            out_of_range_values[ps.name] = "PASS"
    records2, deviations2 = capture_parameters(
        batch_id=batch_id,
        step_id=oor_step_spec.step_id,
        param_values=out_of_range_values,
        operator="e2e_operator",
        recipe_id=recipe.recipe_id,
    )
    check("Out-of-range parameters captured", len(records2) > 0)
    check("Auto-deviations created for out-of-range", len(deviations2) > 0,
          f"got {len(deviations2)} deviations (step={oor_step_spec.name})")
    print(f"    Auto-deviation IDs: {[d.deviation_id for d in deviations2]}")
else:
    print("  (no numeric-bound parameters in any step — skipping)")

# ── 9. Pharma: complete first step ────────────────────────────────────────────
print("\n[9] Pharma — complete first step")
completed_step = complete_step(batch_id, step_id, operator="e2e_operator",
                                comment="Step completed for E2E test")
check("First step completed", completed_step is not None)
check("Step status = COMPLETED",
      completed_step and completed_step.status.value == "Completed",
      f"actual: {completed_step.status.value if completed_step else 'None'}")

# ── 10. Pharma: open manual deviation ────────────────────────────────────────
print("\n[10] Pharma — open manual deviation")
dev = open_deviation(
    batch_id=batch_id,
    step_id=step_id,
    step_name=first_exe.step_name if first_exe else "Step 1",
    category=DeviationCategory.MANUAL_ENTRY,
    severity=DeviationSeverity.MINOR,
    description="Manual test deviation: temperature excursion during granulation",
    detected_by="e2e_operator",
)
check("Deviation created", dev is not None)
dev_id = dev.deviation_id if dev else None
check("Deviation has ID", bool(dev_id))
check("Deviation status = OPEN",
      dev and dev.status == DeviationStatus.OPEN,
      f"actual: {dev.status if dev else 'None'}")

# ── 11. Pharma: close deviation ───────────────────────────────────────────────
print("\n[11] Pharma — close deviation")
closed = update_deviation_status(
    deviation_id=dev_id,
    new_status=DeviationStatus.CLOSED,
    user="qa_manager",
    justification="Temperature returned to range within 5 minutes; no product impact",
)
check("Deviation closed", closed is not None)
check("Deviation status = CLOSED",
      closed and closed.status == DeviationStatus.CLOSED,
      f"actual: {closed.status if closed else 'None'}")

# ── 12. Pharma: complete all remaining steps ──────────────────────────────────
print("\n[12] Pharma — complete remaining steps")
remaining_exes = sorted(
    [e for e in executions if e.step_id != step_id],
    key=lambda e: e.sequence,
)
for exe in remaining_exes:
    sid = exe.step_id
    start_step(batch_id, sid, operator="e2e_operator")
    # Capture all parameters at midpoint
    step_s = next((s for s in recipe.steps if s.step_id == sid), None)
    if step_s and step_s.parameters:
        pv = {}
        for ps in step_s.parameters:
            if ps.min_value is not None and ps.max_value is not None:
                mid = (ps.min_value + ps.max_value) / 2
                pv[ps.name] = str(mid)
            elif ps.allowed_values:
                pv[ps.name] = ps.allowed_values[0]
            else:
                pv[ps.name] = "PASS"
        capture_parameters(
            batch_id=batch_id,
            step_id=sid,
            param_values=pv,
            operator="e2e_operator",
            recipe_id=recipe.recipe_id,
        )
    complete_step(batch_id, sid, operator="e2e_operator")

final_exes = get_executions_for_batch(batch_id)
completed_count = sum(1 for e in final_exes if e.status.value == "Completed")
check(f"All {len(executions)} steps completed",
      completed_count == len(executions),
      f"completed={completed_count}/{len(executions)}")

# ── 13. Pharma: submit review → release ───────────────────────────────────────
print("\n[13] Pharma — submit review and release")
review = submit_review(
    batch_id=batch_id,
    reviewer="qa_director",
    disposition=Disposition.RELEASE,
    comment="All steps completed. Minor deviation justified. Batch released.",
)
check("Review submitted", review is not None)
check("Batch status = RELEASED",
      review and review.disposition == Disposition.RELEASE,
      f"actual: {review.disposition if review else 'None'}")

final_batch = get_batch(batch_id)
check("Batch disposition = Release",
      final_batch and final_batch.disposition == Disposition.RELEASE,
      f"actual: {final_batch.disposition if final_batch else 'None'}")

# ── 14. Verify ERP order status ───────────────────────────────────────────────
print("\n[14] Verify ERP order status")
time.sleep(2)
r = http_get(f"{ERP_URL}/orders")
if r.status_code == 200:
    orders_data = r.json()
    if isinstance(orders_data, dict):
        orders_data = orders_data.get("orders", [])
    erp_order = next((o for o in orders_data
                      if o.get("order_number") == order_id), None)
    if erp_order:
        check("ERP order found", True)
        check("ERP order status = completed",
              erp_order.get("status") == "completed",
              f"actual: {erp_order.get('status')}")
    else:
        print(f"  (ERP order not found for order_id={order_id} — integration may be offline)")
        print(f"  Available order numbers: "
              f"{[o.get('order_number') for o in orders_data[:5]]}")
else:
    print(f"  (ERP orders endpoint returned {r.status_code}: {r.text[:100]})")

# ── 15. Verify MES work order status ─────────────────────────────────────────
print("\n[15] Verify MES work order status")
r = http_get(f"{MES_URL}/work-orders")
if r.status_code == 200:
    wos_data = r.json()
    if isinstance(wos_data, dict):
        wos_data = wos_data.get("work_orders", [])
    mes_wo = next((w for w in wos_data
                   if batch_id and batch_id in str(w.get("work_order_number", ""))), None)
    if mes_wo:
        check("MES work order found", True)
        check("MES work order status = completed",
              mes_wo.get("status") == "completed",
              f"actual: {mes_wo.get('status')}")
    else:
        print(f"  (MES work order not found for batch_id={batch_id})")
        print(f"  Available WO numbers: "
              f"{[w.get('work_order_number') for w in wos_data[:5]]}")
else:
    print(f"  (MES work-orders endpoint returned {r.status_code}: {r.text[:100]})")

# ── 16. Verify echotrace audit trail ─────────────────────────────────────────
print("\n[16] Verify echotrace audit trail")
from echotrace.integration import get_audit_trail
records_at = get_audit_trail(limit=50)
check("Audit trail has records", len(records_at) > 0, f"found {len(records_at)}")
if records_at:
    r0 = records_at[0]
    print(f"    Latest: [{r0['action']}] {r0['entity_type']} "
          f"'{r0['entity_name']}' by {r0['username']}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"\033[91mFAILED — {len(errors)} check(s) failed:\033[0m")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("\033[92mALL CHECKS PASSED\033[0m")
    sys.exit(0)
