"""
Audit Trail Page
Filterable, read-only view of all audit events.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from pharma.app.services.audit_service import get_events_filtered
from pharma.app.utils.helpers import fmt_dt


def render() -> None:
    st.title("📜 Audit Trail")
    st.caption("Immutable record of all critical actions across batches, steps, deviations, and reviews.")
    st.markdown("---")

    st.subheader("Filters")
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        batch_filter = st.text_input("Batch ID contains", "")
        entity_filter = st.selectbox(
            "Entity Type",
            ["All", "Batch", "ProductionOrder", "StepExecution", "Deviation", "ParameterRecord"],
        )
    with fcol2:
        user_filter = st.text_input("User contains", "")
        action_filter = st.selectbox(
            "Action",
            [
                "All",
                "batch created",
                "step started",
                "parameter changed",
                "deviation opened",
                "deviation closed",
                "batch reviewed",
                "disposition changed",
            ],
        )
    with fcol3:
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
        date_to = st.date_input("To Date", value=date.today())

    events = get_events_filtered(
        batch_id=batch_filter or None,
        entity_type=entity_filter if entity_filter != "All" else None,
        user=user_filter or None,
        action=action_filter if action_filter != "All" else None,
        date_from=str(date_from),
        date_to=str(date_to),
    )

    st.markdown("---")
    st.markdown(f"**{len(events)}** event(s) found.")

    if not events:
        st.info("No audit events match the current filters.")
        return

    rows = []
    for e in events:
        rows.append({
            "Event ID": e.event_id,
            "Timestamp": fmt_dt(e.timestamp),
            "User": e.user,
            "Action": e.action,
            "Entity Type": e.entity_type,
            "Entity ID": e.entity_id,
            "Old Value": e.old_value or "—",
            "New Value": e.new_value or "—",
            "Comment": (e.comment or "")[:80],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Export Audit Trail (CSV)",
        data=csv,
        file_name="audit_trail_export.csv",
        mime="text/csv",
    )
