"""
Dashboard Page
Provides an operational overview: batch status summary, deviation counts,
disposition breakdown, recent audit events, live integration health panel,
and an ERP Production Order creation check panel.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from pharma.app.domain.enums import BatchStatus, DeviationSeverity, DeviationStatus, Disposition
from pharma.app.services.audit_service import get_all_events
from pharma.app.services.batch_service import get_all_batches
from pharma.app.services.deviation_service import get_all_deviations
from pharma.app.services.order_service import get_all_orders
from pharma.app.utils.helpers import badge, fmt_dt


def _render_integration_health() -> None:
    """Compact system health strip at the top of the dashboard."""
    st.subheader("Connected Systems")
    try:
        from pharma.app.integration.orchestrator import get_system_health
        health = get_system_health()
    except Exception:
        st.caption("Integration module not loaded.")
        return

    cols = st.columns(3)
    for col, key in zip(cols, ["ERP", "MES", "PCS"]):
        info = health.get(key, {})
        online = info.get("online", False)
        with col:
            if online:
                st.success(f"**{key}** 🟢 Online  \n`{info.get('url', '')}`")
            else:
                st.warning(f"**{key}** 🔴 Offline  \n`{info.get('url', '')}`")


def _render_pcs_strip() -> None:
    """One-line sensor strip from PCS (non-blocking)."""
    try:
        from pharma.app.integration.pcs_client import PCSClient
        pcs = PCSClient()
        if not pcs.is_online():
            return
        machines = pcs.get_all_machines_status()
        if not machines:
            return
        mid = machines[0].get("id")
        if not mid:
            return
        sensors = pcs.get_latest_sensor_data(mid)
        if not sensors:
            return
        st.subheader("PCS – Live Sensor Readings (Machine 1)")
        sensor_cols = st.columns(min(len(sensors), 4))
        for col, s in zip(sensor_cols, sensors[:4]):
            col.metric(
                label=s.get("sensor_name", "sensor"),
                value=f"{round(s.get('value', 0), 2)}",
            )
    except Exception:
        pass  # PCS offline – silent


def _render_erp_production_order_check() -> None:
    """
    ERP Production Order Creation Check Panel.

    For every pharma order that has been dispatched to MES, this panel
    verifies that a corresponding ERP production order was successfully
    created and shows its current status.  If an order is missing from ERP
    it is flagged in red so the operator can investigate or re-trigger the
    integration hook.
    """
    st.subheader("ERP Production Order Check")
    st.caption(
        "Verifies that every pharma order dispatched to MES has a matching "
        "production order in ERP.  Missing or mismatched orders are highlighted."
    )

    pharma_orders = get_all_orders()
    dispatched = [
        o for o in pharma_orders
        if o.status.value not in ("Created",)
    ]

    if not dispatched:
        st.info("No orders have been dispatched to MES yet.")
        return

    # Fetch ERP orders (best-effort)
    erp_orders_by_number: dict = {}
    erp_online = False
    try:
        from pharma.app.integration.erp_client import ERPClient
        erp = ERPClient()
        if erp.is_online():
            erp_online = True
            raw = erp.get_all_orders()
            for o in (raw or []):
                num = o.get("order_number", "")
                if num:
                    erp_orders_by_number[num] = o
    except Exception:
        pass

    if not erp_online:
        st.warning(
            "ERP is offline — cannot verify production order status. "
            "Showing pharma-side order data only."
        )

    rows = []
    for po in dispatched:
        erp_match = erp_orders_by_number.get(po.order_id)
        if erp_online:
            if erp_match:
                erp_status = erp_match.get("status", "unknown")
                erp_id = str(erp_match.get("id", "—"))
                sync_status = "✅ Matched"
            else:
                erp_status = "NOT FOUND"
                erp_id = "—"
                sync_status = "❌ Missing in ERP"
        else:
            erp_status = "—"
            erp_id = "—"
            sync_status = "⚠️ ERP Offline"

        rows.append({
            "Pharma Order ID": po.order_id,
            "Product": po.product_name,
            "Qty": f"{po.quantity:,.0f} {po.unit}",
            "Pharma Status": po.status.value,
            "ERP Order ID": erp_id,
            "ERP Status": erp_status,
            "ERP Sync": sync_status,
            "Due Date": po.due_date,
        })

    df = pd.DataFrame(rows)

    # Colour-code the ERP Sync column
    def _highlight_sync(val: str) -> str:
        if "Missing" in val:
            return "background-color: #fde8e8; color: #c0392b; font-weight: bold"
        if "Offline" in val:
            return "background-color: #fef9e7; color: #d35400"
        return "background-color: #eafaf1; color: #1e8449"

    styled = df.style.applymap(_highlight_sync, subset=["ERP Sync"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Summary metrics
    if erp_online:
        matched = sum(1 for r in rows if "Matched" in r["ERP Sync"])
        missing = sum(1 for r in rows if "Missing" in r["ERP Sync"])
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Orders Dispatched", len(rows))
        mc2.metric("ERP Matched", matched)
        mc3.metric("Missing in ERP", missing,
                   delta=f"{missing} need attention" if missing else "All good",
                   delta_color="inverse" if missing else "normal")

    # Re-trigger button for missing orders
    if erp_online:
        missing_orders = [po for po in dispatched
                          if po.order_id not in erp_orders_by_number]
        if missing_orders:
            st.markdown("---")
            st.warning(
                f"**{len(missing_orders)} order(s) are missing from ERP.** "
                "Use the button below to re-trigger the ERP integration hook."
            )
            if st.button("🔄 Re-trigger ERP Sync for Missing Orders",
                         type="primary"):
                from pharma.app.integration import orchestrator as orch
                re_synced = 0
                for po in missing_orders:
                    try:
                        orch.on_order_created(
                            pharma_order_id=po.order_id,
                            product_code=po.product_code,
                            product_name=po.product_name,
                            quantity=po.quantity,
                            due_date=po.due_date,
                            site=po.site,
                        )
                        re_synced += 1
                    except Exception as exc:
                        st.error(f"Failed to re-sync {po.order_id}: {exc}")
                if re_synced:
                    st.success(
                        f"Re-triggered ERP sync for {re_synced} order(s). "
                        "Refresh the page to see updated status."
                    )


def render() -> None:
    st.title("📊 Operations Dashboard")
    st.caption(
        "Real-time overview of batch execution status, deviations, "
        "system integration, and ERP production order verification."
    )
    st.markdown("---")

    # ── Integration health ────────────────────────────────────────────────
    _render_integration_health()
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

    # ── PCS sensor strip ──────────────────────────────────────────────────
    _render_pcs_strip()

    # ── ERP Production Order Check ────────────────────────────────────────
    st.markdown("---")
    _render_erp_production_order_check()

    # ── Charts row ────────────────────────────────────────────────────────────
    st.markdown("---")
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
