"""
Review & Release Page
Batch completeness check, deviation summary, and disposition decision.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pharma.app.domain.enums import BatchStatus, Disposition, ReviewStatus, StepStatus
from pharma.app.services.batch_service import get_all_batches, get_batch, get_executions_for_batch
from pharma.app.services.deviation_service import get_deviations_for_batch
from pharma.app.services.review_service import compute_review, get_review_for_batch, submit_review
from pharma.app.utils.helpers import badge, fmt_dt


def render() -> None:
    st.title("✅ Batch Review & Release")
    st.caption("Completeness check, deviation summary, and disposition decision for batch release.")
    st.markdown("---")

    batches = get_all_batches()
    if not batches:
        st.info("No batches available.")
        return

    batch_options = {f"{b.batch_id} – {b.product_name} ({b.status.value})": b.batch_id for b in batches}
    selected_label = st.selectbox("Select Batch for Review", list(batch_options.keys()))
    batch_id = batch_options[selected_label]
    batch = get_batch(batch_id)

    if not batch:
        return

    st.markdown("---")

    # ── Batch summary ─────────────────────────────────────────────────────────
    st.subheader("Batch Summary")
    hcol1, hcol2, hcol3, hcol4 = st.columns(4)
    hcol1.metric("Batch ID", batch.batch_id)
    hcol2.metric("Product", batch.product_name)
    hcol3.metric("Status", batch.status.value)
    hcol4.metric("Disposition", batch.disposition.value)

    col5, col6, col7 = st.columns(3)
    col5.metric("Site", batch.site)
    col6.metric("Quantity", f"{batch.quantity} {batch.unit}")
    col7.metric("Deviations", batch.deviation_count)

    st.markdown("---")

    # ── Completeness check ────────────────────────────────────────────────────
    st.subheader("Completeness Check")
    try:
        decision = compute_review(batch_id)
    except Exception as e:
        st.error(f"Could not compute review: {e}")
        return

    # Gauge chart for completeness
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=decision.completeness_score,
        title={"text": "Batch Completeness (%)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#2ecc71" if decision.completeness_score >= 100 else "#e67e22"},
            "steps": [
                {"range": [0, 50], "color": "#fadbd8"},
                {"range": [50, 80], "color": "#fdebd0"},
                {"range": [80, 100], "color": "#d5f5e3"},
            ],
            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 100},
        },
    ))
    fig.update_layout(height=250, margin=dict(t=20, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    # Checklist
    checks = {
        "All mandatory steps completed": len(decision.incomplete_steps) == 0,
        "No open critical deviations": decision.critical_deviations == 0,
        "No open deviations": decision.open_deviations == 0,
        "No out-of-spec parameters": len(decision.missing_parameters) == 0,
        "Review completed": batch.review_status == ReviewStatus.COMPLETED,
    }

    check_col1, check_col2 = st.columns(2)
    items = list(checks.items())
    for i, (label, passed) in enumerate(items):
        col = check_col1 if i % 2 == 0 else check_col2
        icon = "✅" if passed else "❌"
        col.markdown(f"{icon} {label}")

    if decision.incomplete_steps:
        st.warning(f"Incomplete mandatory steps: {', '.join(decision.incomplete_steps)}")
    if decision.missing_parameters:
        st.warning(f"Out-of-spec / missing parameters: {', '.join(set(decision.missing_parameters))}")

    st.markdown("---")

    # ── Step status table ─────────────────────────────────────────────────────
    st.subheader("Step Execution Summary")
    executions = get_executions_for_batch(batch_id)
    if executions:
        rows = []
        for exe in executions:
            rows.append({
                "Seq": exe.sequence,
                "Step": exe.step_name,
                "Status": badge(exe.status.value),
                "Operator": exe.operator or "—",
                "Params": len(exe.parameters),
                "Out-of-Spec": sum(1 for p in exe.parameters if not p.within_spec),
                "Completed": fmt_dt(exe.completed_at),
            })
        df_steps = pd.DataFrame(rows)
        st.dataframe(df_steps, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Deviation summary ─────────────────────────────────────────────────────
    st.subheader("Deviation Summary")
    deviations = get_deviations_for_batch(batch_id)
    if deviations:
        rows_dev = []
        for d in deviations:
            rows_dev.append({
                "Deviation ID": d.deviation_id,
                "Step": d.step_name,
                "Category": d.category.value,
                "Severity": d.severity.value,
                "Status": badge(d.status.value),
                "Description": d.description[:60] + ("…" if len(d.description) > 60 else ""),
            })
        df_dev = pd.DataFrame(rows_dev)
        st.dataframe(df_dev, use_container_width=True, hide_index=True)
    else:
        st.success("No deviations recorded for this batch.")

    st.markdown("---")

    # ── Release recommendation ────────────────────────────────────────────────
    st.subheader("Release Recommendation")

    disp_color = {
        Disposition.RELEASE: "success",
        Disposition.RELEASE_WITH_COMMENTS: "warning",
        Disposition.REJECT_HOLD: "error",
        Disposition.PENDING: "info",
    }
    disp_fn = getattr(st, disp_color.get(decision.disposition, "info"))
    disp_fn(f"**Recommended Disposition:** {decision.disposition.value}  \n{decision.comment}")

    # ── Existing review ───────────────────────────────────────────────────────
    existing_review = get_review_for_batch(batch_id)
    if existing_review and existing_review.reviewer:
        st.info(
            f"**Review already submitted** by {existing_review.reviewer} "
            f"on {fmt_dt(existing_review.timestamp)}: "
            f"**{existing_review.disposition.value}**  \n{existing_review.comment}"
        )

    # ── Submit review form ────────────────────────────────────────────────────
    if batch.status not in (BatchStatus.RELEASED, BatchStatus.REJECTED):
        st.markdown("---")
        st.subheader("Submit Review Decision")
        with st.form(f"review_form_{batch_id}"):
            reviewer = st.text_input("Reviewer ID", value="QA-001")
            disposition = st.selectbox(
                "Disposition Decision",
                [d.value for d in Disposition if d != Disposition.PENDING],
                index=[d.value for d in Disposition if d != Disposition.PENDING].index(
                    decision.disposition.value
                ) if decision.disposition != Disposition.PENDING else 0,
            )
            comment = st.text_area("Review Comment / Justification")
            submitted = st.form_submit_button("Submit Review")
            if submitted and reviewer:
                result = submit_review(
                    batch_id=batch_id,
                    reviewer=reviewer,
                    disposition=Disposition(disposition),
                    comment=comment,
                )
                st.success(f"Review submitted. Disposition: **{result.disposition.value}**")
                st.rerun()
    else:
        st.success(f"Batch has been **{batch.status.value}**. No further review action required.")
