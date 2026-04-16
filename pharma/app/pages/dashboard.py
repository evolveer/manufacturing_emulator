"""
Dashboard Page
Provides an operational overview: batch status summary, deviation counts,
disposition breakdown, and recent audit events.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pharma.app.domain.enums import BatchStatus, DeviationSeverity, DeviationStatus, Disposition
from pharma.app.services.audit_service import get_all_events
from pharma.app.services.batch_service import get_all_batches
from pharma.app.services.deviation_service import get_all_deviations
from pharma.app.services.order_service import get_all_orders
from pharma.app.utils.helpers import badge, fmt_dt


def render() -> None:
    st.title("📊 Operations Dashboard")
    st.caption("Real-time overview of batch execution status, deviations, and recent activity.")
    st.markdown("---")

    batches = get_all_batches()
    orders = get_all_orders()
    deviations = get_all_deviations()
    events = get_all_events()

    # ── KPI row ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    total_batches = len(batches)
    in_progress = sum(1 for b in batches if b.status == BatchStatus.IN_PROGRESS)
    completed = sum(1 for b in batches if b.status in (BatchStatus.COMPLETED, BatchStatus.RELEASED))
    released = sum(1 for b in batches if b.status == BatchStatus.RELEASED or b.disposition == Disposition.RELEASE)
    on_hold = sum(1 for b in batches if b.status in (BatchStatus.ON_HOLD, BatchStatus.REJECTED))
    open_devs = sum(1 for d in deviations if d.status in (DeviationStatus.OPEN, DeviationStatus.INVESTIGATING, DeviationStatus.ESCALATED))
    critical_devs = sum(1 for d in deviations if d.severity == DeviationSeverity.CRITICAL and d.status not in (DeviationStatus.CLOSED,))

    col1.metric("Total Batches", total_batches)
    col2.metric("In Progress", in_progress)
    col3.metric("Completed / Released", completed)
    col4.metric("Open Deviations", open_devs, delta=f"{critical_devs} critical", delta_color="inverse")
    col5.metric("On Hold / Rejected", on_hold)

    st.markdown("---")

    # ── Charts row ────────────────────────────────────────────────────────────
    chart_col1, chart_col2, chart_col3 = st.columns(3)

    with chart_col1:
        st.subheader("Batch Status Distribution")
        if batches:
            status_counts = {}
            for b in batches:
                status_counts[b.status.value] = status_counts.get(b.status.value, 0) + 1
            fig = px.pie(
                names=list(status_counts.keys()),
                values=list(status_counts.values()),
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No batches yet.")

    with chart_col2:
        st.subheader("Disposition Breakdown")
        if batches:
            disp_counts = {}
            for b in batches:
                disp_counts[b.disposition.value] = disp_counts.get(b.disposition.value, 0) + 1
            color_map = {
                "Release": "#2ecc71",
                "Release with Comments": "#f39c12",
                "Reject / Hold": "#e74c3c",
                "Pending": "#95a5a6",
            }
            fig2 = px.bar(
                x=list(disp_counts.keys()),
                y=list(disp_counts.values()),
                color=list(disp_counts.keys()),
                color_discrete_map=color_map,
                labels={"x": "Disposition", "y": "Count"},
            )
            fig2.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No batches yet.")

    with chart_col3:
        st.subheader("Deviation Severity")
        if deviations:
            sev_counts = {}
            for d in deviations:
                sev_counts[d.severity.value] = sev_counts.get(d.severity.value, 0) + 1
            color_sev = {"Minor": "#f1c40f", "Major": "#e67e22", "Critical": "#e74c3c"}
            fig3 = px.bar(
                x=list(sev_counts.keys()),
                y=list(sev_counts.values()),
                color=list(sev_counts.keys()),
                color_discrete_map=color_sev,
                labels={"x": "Severity", "y": "Count"},
            )
            fig3.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No deviations yet.")

    st.markdown("---")

    # ── Batch summary table ───────────────────────────────────────────────────
    st.subheader("Active Batches")
    if batches:
        rows = []
        for b in batches:
            rows.append({
                "Batch ID": b.batch_id,
                "Product": b.product_name,
                "Site": b.site,
                "Status": badge(b.status.value),
                "Disposition": badge(b.disposition.value),
                "Deviations": b.deviation_count,
                "Created": fmt_dt(b.created_at),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No batches found. Create a production order and instantiate a batch.")

    st.markdown("---")

    # ── Recent audit events ───────────────────────────────────────────────────
    st.subheader("Recent Audit Events")
    if events:
        recent = sorted(events, key=lambda e: e.timestamp, reverse=True)[:10]
        rows = []
        for e in recent:
            rows.append({
                "Timestamp": fmt_dt(e.timestamp),
                "User": e.user,
                "Action": e.action,
                "Entity": f"{e.entity_type} / {e.entity_id}",
                "New Value": e.new_value or "—",
                "Comment": (e.comment or "")[:60],
            })
        df_audit = pd.DataFrame(rows)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)
    else:
        st.info("No audit events recorded yet.")
