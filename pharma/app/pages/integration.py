"""
Integration Status Page
Shows live connectivity to ERP, MES, and PCS systems, live machine sensor data,
ERP inventory snapshot, and MES active work orders.
"""

from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger("pharma.pages.integration")


def _health_badge(online: bool) -> str:
    return "🟢 Online" if online else "🔴 Offline"


def render() -> None:
    st.title("System Integration Status")
    st.caption(
        "Live connectivity and data exchange with ERP (port 5001), MES (port 5002), and PCS (port 5003)."
    )

    # ── Health checks ──────────────────────────────────────────────────────
    st.subheader("System Health")
    try:
        from ..integration.orchestrator import get_system_health
        health = get_system_health()
    except Exception as exc:
        st.error(f"Could not load integration module: {exc}")
        return

    col_erp, col_mes, col_pcs = st.columns(3)
    for col, key in zip([col_erp, col_mes, col_pcs], ["ERP", "MES", "PCS"]):
        info = health.get(key, {})
        with col:
            online = info.get("online", False)
            st.metric(
                label=key,
                value=_health_badge(online),
                delta=info.get("url", ""),
                delta_color="off",
            )
            if online:
                st.success(f"{key} is reachable at {info.get('url')}")
            else:
                st.warning(
                    f"{key} is **offline** ({info.get('url')}). "
                    "Pharma simulator runs in standalone mode – integration calls are queued and will "
                    "retry when the system comes online."
                )

    st.divider()

    # ── ERP inventory ──────────────────────────────────────────────────────
    st.subheader("ERP – Material Inventory Snapshot")
    erp_online = health.get("ERP", {}).get("online", False)
    if erp_online:
        try:
            from ..integration.orchestrator import get_erp_inventory_snapshot
            materials = get_erp_inventory_snapshot()
            if materials:
                rows = [
                    {
                        "Code": m.get("code", ""),
                        "Name": m.get("name", ""),
                        "Stock": m.get("stock_quantity", 0),
                        "Unit": m.get("unit", ""),
                        "Min Level": m.get("min_stock_level", 0),
                        "Status": "⚠ Low" if m.get("stock_quantity", 0) < m.get("min_stock_level", 0) else "OK",
                    }
                    for m in materials
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No materials found in ERP inventory.")
        except Exception as exc:
            st.error(f"ERP inventory fetch failed: {exc}")
    else:
        st.info("ERP is offline – inventory data unavailable.")

    # ── ERP Products ───────────────────────────────────────────────────────
    st.subheader("ERP – Product Catalogue")
    if erp_online:
        try:
            from ..integration.orchestrator import get_erp_products
            products = get_erp_products()
            if products:
                rows = [
                    {
                        "Code": p.get("code", ""),
                        "Name": p.get("name", ""),
                        "Category": p.get("category", ""),
                        "Stock": p.get("stock_quantity", 0),
                    }
                    for p in products
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No products found in ERP catalogue.")
        except Exception as exc:
            st.error(f"ERP product fetch failed: {exc}")
    else:
        st.info("ERP is offline – product data unavailable.")

    st.divider()

    # ── MES work orders ────────────────────────────────────────────────────
    st.subheader("MES – Active Work Orders")
    mes_online = health.get("MES", {}).get("online", False)
    if mes_online:
        try:
            from ..integration.erp_client import ERPClient
            from ..integration.mes_client import MESClient
            mes = MESClient()
            work_orders = mes.get_work_orders()
            if work_orders:
                rows = [
                    {
                        "WO Number": wo.get("work_order_number", ""),
                        "Status": wo.get("status", ""),
                        "Product ID": wo.get("product_id", ""),
                        "Quantity": wo.get("quantity", 0),
                        "Good": wo.get("good_count", 0),
                        "Reject": wo.get("reject_count", 0),
                    }
                    for wo in work_orders
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No work orders found in MES.")
        except Exception as exc:
            st.error(f"MES work order fetch failed: {exc}")
    else:
        st.info("MES is offline – work order data unavailable.")

    # ── MES quality checks ─────────────────────────────────────────────────
    st.subheader("MES – Recent Quality Checks")
    if mes_online:
        try:
            mes = MESClient()
            qc_list = mes.get_quality_checks()
            if qc_list:
                rows = [
                    {
                        "WO ID": qc.get("work_order_id", ""),
                        "Parameter": qc.get("parameter_name", ""),
                        "Value": qc.get("actual_value", ""),
                        "Result": qc.get("result", ""),
                        "Type": qc.get("check_type", ""),
                        "Notes": qc.get("notes", ""),
                    }
                    for qc in qc_list[-50:]  # last 50
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No quality checks recorded in MES.")
        except Exception as exc:
            st.error(f"MES quality check fetch failed: {exc}")
    else:
        st.info("MES is offline – quality check data unavailable.")

    st.divider()

    # ── PCS live machine data ──────────────────────────────────────────────
    st.subheader("PCS – Live Machine Data")
    pcs_online = health.get("PCS", {}).get("online", False)
    if pcs_online:
        try:
            from ..integration.orchestrator import get_live_machine_data
            machine_data = get_live_machine_data()
            machines = machine_data.get("machines", [])
            if machines:
                for entry in machines:
                    m = entry.get("machine", {})
                    machine_id = m.get("id", "?")
                    machine_name = m.get("machine_id", f"Machine {machine_id}")
                    state = entry.get("state") or {}
                    status = state.get("status", m.get("status", "unknown"))

                    with st.expander(f"Machine {machine_name} – {status.upper()}", expanded=True):
                        c1, c2 = st.columns(2)

                        # Parameters
                        params = entry.get("parameters", [])
                        if params:
                            with c1:
                                st.markdown("**Process Parameters**")
                                param_rows = [
                                    {
                                        "Parameter": p.get("parameter_name", ""),
                                        "Current": p.get("current_value", ""),
                                        "Setpoint": p.get("set_point", ""),
                                        "Min": p.get("min_value", ""),
                                        "Max": p.get("max_value", ""),
                                        "Unit": p.get("unit", ""),
                                    }
                                    for p in params
                                ]
                                st.dataframe(param_rows, use_container_width=True)

                        # Sensors
                        sensors = entry.get("sensors", [])
                        if sensors:
                            with c2:
                                st.markdown("**Sensor Readings**")
                                sensor_rows = [
                                    {
                                        "Sensor": s.get("sensor_name", ""),
                                        "Value": round(s.get("value", 0), 3),
                                        "Timestamp": s.get("timestamp", ""),
                                    }
                                    for s in sensors
                                ]
                                st.dataframe(sensor_rows, use_container_width=True)

                        # Alarms
                        alarms = entry.get("alarms", [])
                        if alarms:
                            st.markdown("**Active Alarms**")
                            alarm_rows = [
                                {
                                    "ID": a.get("id", ""),
                                    "Type": a.get("alarm_type", ""),
                                    "Severity": a.get("severity", ""),
                                    "Message": a.get("message", ""),
                                    "Status": a.get("status", ""),
                                }
                                for a in alarms
                            ]
                            st.dataframe(alarm_rows, use_container_width=True)
            else:
                st.info("No machines found in PCS.")
        except Exception as exc:
            st.error(f"PCS data fetch failed: {exc}")
    else:
        st.info("PCS is offline – machine data unavailable.")

    st.divider()

    # ── Integration event log ──────────────────────────────────────────────
    st.subheader("Integration Event Log (Pharma Audit Trail – Integration Actions)")
    try:
        from ..services.audit_service import get_all_events
        events = get_all_events()
        integration_events = [
            e for e in events
            if any(
                kw in (e.action or "").lower()
                for kw in ("order created", "order sent", "batch created", "batch reviewed",
                           "step started", "step completed", "parameter captured", "deviation opened")
            )
        ]
        if integration_events:
            rows = [
                {
                    "Timestamp": e.timestamp[:19],
                    "User": e.user,
                    "Action": e.action,
                    "Entity": e.entity_type,
                    "ID": e.entity_id,
                    "New Value": e.new_value or "",
                    "Comment": (e.comment or "")[:80],
                }
                for e in reversed(integration_events[-100:])
            ]
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No integration events recorded yet.")
    except Exception as exc:
        st.error(f"Audit trail fetch failed: {exc}")
