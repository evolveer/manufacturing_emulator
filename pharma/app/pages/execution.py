"""
Batch Execution Page
Step-by-step batch execution: start steps, enter parameters, complete or log issues.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pharma.app.domain.enums import DeviationSeverity, StepStatus
from pharma.app.services.batch_service import get_all_batches, get_batch, get_executions_for_batch
from pharma.app.services.execution_service import (
    capture_parameters,
    complete_step,
    mark_step_deviated,
    skip_step,
    start_step,
)
from pharma.app.services.recipe_service import get_recipe
from pharma.app.utils.helpers import badge, fmt_dt

_STATUS_ICON = {
    "Not Started": "⚪",
    "Ready": "🔵",
    "In Progress": "🟡",
    "Completed": "✅",
    "Deviated": "🟠",
    "Skipped": "⏭️",
    "Blocked": "🔴",
    "Under Review": "🔍",
}


def render() -> None:
    st.title("🔬 Batch Execution")
    st.caption("Execute batch steps, capture process parameters, and log issues.")
    st.markdown("---")

    batches = get_all_batches()
    if not batches:
        st.info("No batches available. Create a production order and instantiate a batch first.")
        return

    batch_options = {f"{b.batch_id} – {b.product_name} ({b.status.value})": b.batch_id for b in batches}
    selected_label = st.selectbox("Select Batch", list(batch_options.keys()))
    batch_id = batch_options[selected_label]
    batch = get_batch(batch_id)

    if not batch:
        st.error("Batch not found.")
        return

    # ── Batch header ──────────────────────────────────────────────────────────
    st.markdown("---")
    hcol1, hcol2, hcol3, hcol4 = st.columns(4)
    hcol1.metric("Batch ID", batch.batch_id)
    hcol2.metric("Product", batch.product_name)
    hcol3.metric("Status", batch.status.value)
    hcol4.metric("Deviations", batch.deviation_count)

    col5, col6, col7 = st.columns(3)
    col5.metric("Site", batch.site)
    col6.metric("Quantity", f"{batch.quantity} {batch.unit}")
    col7.metric("Created", fmt_dt(batch.created_at))

    st.markdown("---")

    # ── Step list ─────────────────────────────────────────────────────────────
    executions = get_executions_for_batch(batch_id)
    recipe = get_recipe(batch.recipe_id)

    if not executions:
        st.warning("No step executions found for this batch.")
        return

    st.subheader("Recipe Steps")

    # Summary table
    rows = []
    for exe in executions:
        icon = _STATUS_ICON.get(exe.status.value, "⚪")
        rows.append({
            "Seq": exe.sequence,
            "Step": exe.step_name,
            "Status": f"{icon} {exe.status.value}",
            "Operator": exe.operator or "—",
            "Started": fmt_dt(exe.started_at),
            "Completed": fmt_dt(exe.completed_at),
            "Params Captured": len(exe.parameters),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Step execution panel ──────────────────────────────────────────────────
    st.subheader("Execute a Step")

    actionable_statuses = [StepStatus.NOT_STARTED, StepStatus.READY, StepStatus.IN_PROGRESS]
    actionable_execs = [e for e in executions if e.status in actionable_statuses]

    if not actionable_execs:
        st.success("All steps have been processed for this batch.")
        return

    step_options = {f"[{e.sequence}] {e.step_name} ({e.status.value})": e.execution_id for e in actionable_execs}
    selected_step_label = st.selectbox("Select Step to Execute", list(step_options.keys()))
    selected_exe_id = step_options[selected_step_label]
    exe = next((e for e in executions if e.execution_id == selected_exe_id), None)

    if not exe:
        return

    # Get recipe step spec
    step_spec = None
    if recipe:
        step_spec = next((s for s in recipe.steps if s.step_id == exe.step_id), None)

    st.markdown(f"**Step:** {exe.step_name}")
    if step_spec:
        st.markdown(f"**Description:** {step_spec.description}")
        st.markdown(f"**Acceptance Criteria:** {step_spec.acceptance_criteria}")
        st.markdown(f"**Expected Duration:** {step_spec.expected_duration_min} min")

    operator = st.text_input("Operator ID", value="OP-001", key=f"op_{exe.execution_id}")

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)

    # ── Start Step ────────────────────────────────────────────────────────────
    with action_col1:
        if exe.status in (StepStatus.NOT_STARTED, StepStatus.READY):
            if st.button("▶️ Start Step", key=f"start_{exe.execution_id}"):
                updated = start_step(batch_id, exe.step_id, operator)
                if updated:
                    st.success(f"Step '{exe.step_name}' started.")
                    st.rerun()

    # ── Complete Step ─────────────────────────────────────────────────────────
    with action_col2:
        if exe.status == StepStatus.IN_PROGRESS:
            if st.button("✅ Complete Step", key=f"complete_{exe.execution_id}"):
                st.session_state[f"show_complete_{exe.execution_id}"] = True

    # ── Log Issue / Deviation ─────────────────────────────────────────────────
    with action_col3:
        if exe.status == StepStatus.IN_PROGRESS:
            if st.button("⚠️ Log Issue", key=f"issue_{exe.execution_id}"):
                st.session_state[f"show_issue_{exe.execution_id}"] = True

    # ── Skip Step ─────────────────────────────────────────────────────────────
    with action_col4:
        if exe.status in (StepStatus.NOT_STARTED, StepStatus.READY, StepStatus.IN_PROGRESS):
            if st.button("⏭️ Skip Step", key=f"skip_{exe.execution_id}"):
                st.session_state[f"show_skip_{exe.execution_id}"] = True

    # ── Complete Step Form ────────────────────────────────────────────────────
    if st.session_state.get(f"show_complete_{exe.execution_id}"):
        st.markdown("---")
        st.markdown("#### Parameter Entry")
        with st.form(f"complete_form_{exe.execution_id}"):
            param_values: dict = {}
            if step_spec and step_spec.parameters:
                for ps in step_spec.parameters:
                    label = f"{ps.name} ({ps.unit})" if ps.unit else ps.name
                    hint = ""
                    if ps.min_value is not None and ps.max_value is not None:
                        hint = f"Range: {ps.min_value}–{ps.max_value} {ps.unit}"
                    elif ps.allowed_values:
                        hint = f"Allowed: {', '.join(ps.allowed_values)}"
                    val = st.text_input(label, help=hint, key=f"param_{exe.execution_id}_{ps.name}")
                    param_values[ps.name] = val
            else:
                st.info("No parameters defined for this step.")

            comment = st.text_area("Completion Comment", key=f"comment_{exe.execution_id}")
            submitted = st.form_submit_button("Submit & Complete Step")
            if submitted:
                # Capture parameters first
                if param_values:
                    records, devs = capture_parameters(
                        batch_id=batch_id,
                        step_id=exe.step_id,
                        param_values={k: v for k, v in param_values.items() if v.strip()},
                        operator=operator,
                        recipe_id=batch.recipe_id,
                    )
                    if devs:
                        st.warning(f"{len(devs)} deviation(s) triggered by out-of-spec parameters.")
                # Complete step
                complete_step(batch_id, exe.step_id, operator, comment)
                st.session_state.pop(f"show_complete_{exe.execution_id}", None)
                st.success(f"Step '{exe.step_name}' completed.")
                st.rerun()

    # ── Issue Form ────────────────────────────────────────────────────────────
    if st.session_state.get(f"show_issue_{exe.execution_id}"):
        st.markdown("---")
        st.markdown("#### Log Deviation / Issue")
        with st.form(f"issue_form_{exe.execution_id}"):
            description = st.text_area("Issue Description", key=f"issue_desc_{exe.execution_id}")
            severity = st.selectbox(
                "Severity",
                [s.value for s in DeviationSeverity],
                key=f"issue_sev_{exe.execution_id}",
            )
            comment = st.text_area("Comment", key=f"issue_comment_{exe.execution_id}")
            submitted = st.form_submit_button("Log Issue")
            if submitted and description:
                exe_updated, dev = mark_step_deviated(
                    batch_id=batch_id,
                    step_id=exe.step_id,
                    operator=operator,
                    description=description,
                    severity=DeviationSeverity(severity),
                    comment=comment,
                )
                st.session_state.pop(f"show_issue_{exe.execution_id}", None)
                st.warning(f"Deviation {dev.deviation_id} opened for step '{exe.step_name}'.")
                st.rerun()

    # ── Skip Form ─────────────────────────────────────────────────────────────
    if st.session_state.get(f"show_skip_{exe.execution_id}"):
        st.markdown("---")
        st.markdown("#### Skip Step")
        with st.form(f"skip_form_{exe.execution_id}"):
            reason = st.text_area("Reason for Skipping", key=f"skip_reason_{exe.execution_id}")
            submitted = st.form_submit_button("Confirm Skip")
            if submitted and reason:
                required = step_spec.required if step_spec else False
                exe_updated, dev = skip_step(
                    batch_id=batch_id,
                    step_id=exe.step_id,
                    operator=operator,
                    reason=reason,
                    step_required=required,
                )
                st.session_state.pop(f"show_skip_{exe.execution_id}", None)
                if dev:
                    st.error(f"Critical deviation {dev.deviation_id} opened: mandatory step skipped.")
                else:
                    st.info(f"Step '{exe.step_name}' skipped.")
                st.rerun()

    # ── Captured Parameters ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Captured Parameters (Current Batch)")
    all_params = []
    for e in executions:
        for p in e.parameters:
            all_params.append({
                "Step": e.step_name,
                "Parameter": p.name,
                "Value": p.value,
                "Unit": p.unit,
                "Within Spec": "✅" if p.within_spec else "❌",
                "Recorded By": p.recorded_by,
                "Recorded At": fmt_dt(p.recorded_at),
            })
    if all_params:
        df_params = pd.DataFrame(all_params)
        st.dataframe(df_params, use_container_width=True, hide_index=True)
    else:
        st.info("No parameters captured yet.")
