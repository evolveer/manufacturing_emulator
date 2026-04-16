"""
Deviations Page
Lists all deviations, allows status updates, justification, and closure.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pharma.app.domain.enums import DeviationStatus
from pharma.app.services.deviation_service import (
    get_all_deviations,
    get_deviation,
    update_deviation_status,
)
from pharma.app.utils.helpers import badge, fmt_dt

_SEV_COLOR = {
    "Minor": "🟡",
    "Major": "🟠",
    "Critical": "🔴",
}


def render() -> None:
    st.title("⚠️ Deviations")
    st.caption("Non-conformance records: review, justify, and close deviations.")
    st.markdown("---")

    deviations = get_all_deviations()

    if not deviations:
        st.info("No deviations recorded.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        status_filter = st.selectbox("Filter by Status", ["All"] + [s.value for s in DeviationStatus])
    with fcol2:
        severity_filter = st.selectbox("Filter by Severity", ["All", "Minor", "Major", "Critical"])
    with fcol3:
        batch_filter = st.text_input("Filter by Batch ID", "")

    filtered = deviations
    if status_filter != "All":
        filtered = [d for d in filtered if d.status.value == status_filter]
    if severity_filter != "All":
        filtered = [d for d in filtered if d.severity.value == severity_filter]
    if batch_filter:
        filtered = [d for d in filtered if batch_filter.upper() in d.batch_id.upper()]

    # ── Summary table ─────────────────────────────────────────────────────────
    rows = []
    for d in filtered:
        rows.append({
            "Deviation ID": d.deviation_id,
            "Batch ID": d.batch_id,
            "Step": d.step_name or d.step_id,
            "Category": d.category.value,
            "Severity": f"{_SEV_COLOR.get(d.severity.value, '')} {d.severity.value}",
            "Status": badge(d.status.value),
            "Description": d.description[:60] + ("…" if len(d.description) > 60 else ""),
            "Detected": fmt_dt(d.detected_at),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown(f"**{len(filtered)}** deviation(s) shown.")
    st.markdown("---")

    # ── Detail / Action panel ─────────────────────────────────────────────────
    st.subheader("Deviation Detail & Actions")

    dev_ids = [d.deviation_id for d in filtered]
    if not dev_ids:
        st.info("No deviations match the current filter.")
        return

    selected_id = st.selectbox("Select Deviation", dev_ids)
    dev = get_deviation(selected_id)

    if not dev:
        return

    # Display detail
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown(f"**Deviation ID:** {dev.deviation_id}")
        st.markdown(f"**Batch ID:** {dev.batch_id}")
        st.markdown(f"**Step:** {dev.step_name or dev.step_id}")
        st.markdown(f"**Category:** {dev.category.value}")
        st.markdown(f"**Severity:** {_SEV_COLOR.get(dev.severity.value, '')} {dev.severity.value}")
        st.markdown(f"**Status:** {badge(dev.status.value)}")
        st.markdown(f"**Detected by:** {dev.detected_by} at {fmt_dt(dev.detected_at)}")

    with dcol2:
        st.markdown(f"**Description:**")
        st.info(dev.description)
        if dev.justification:
            st.markdown(f"**Justification:** {dev.justification}")
        if dev.corrective_action:
            st.markdown(f"**Corrective Action:** {dev.corrective_action}")
        if dev.disposition:
            st.markdown(f"**Disposition:** {dev.disposition}")
        if dev.closed_at:
            st.markdown(f"**Closed:** {fmt_dt(dev.closed_at)} by {dev.closed_by}")

    # ── Status transition actions ─────────────────────────────────────────────
    if dev.status not in (DeviationStatus.CLOSED,):
        st.markdown("---")
        st.markdown("#### Update Deviation Status")

        with st.form(f"dev_action_{dev.deviation_id}"):
            new_status = st.selectbox(
                "New Status",
                [s.value for s in DeviationStatus if s != dev.status],
                key=f"new_status_{dev.deviation_id}",
            )
            user = st.text_input("Your User ID", value="QA-001", key=f"dev_user_{dev.deviation_id}")
            justification = st.text_area("Justification / Investigation Notes", key=f"just_{dev.deviation_id}")
            corrective_action = st.text_area("Corrective Action", key=f"ca_{dev.deviation_id}")
            disposition = st.text_input("Disposition", key=f"disp_{dev.deviation_id}")

            submitted = st.form_submit_button("Update Deviation")
            if submitted:
                updated = update_deviation_status(
                    deviation_id=dev.deviation_id,
                    new_status=DeviationStatus(new_status),
                    user=user,
                    justification=justification or None,
                    corrective_action=corrective_action or None,
                    disposition=disposition or None,
                )
                if updated:
                    st.success(f"Deviation {dev.deviation_id} updated to '{new_status}'.")
                    st.rerun()
    else:
        st.success("This deviation is closed.")
