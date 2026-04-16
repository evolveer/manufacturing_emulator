"""
Pharma Batch Execution Simulator
Main Streamlit application entry point.
"""

import sys
import os

# Ensure the pharma package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st

st.set_page_config(
    page_title="Pharma Batch Execution Simulator",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Seed demo data on first run
from pharma.app.data.demo_loader import load_all_demo_scenarios
load_all_demo_scenarios()

# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("⚗️ Pharma Batch Simulator")
st.sidebar.markdown("---")

# System health indicator (non-blocking)
try:
    from pharma.app.integration.orchestrator import get_system_health
    health = get_system_health()
    erp_ok = health.get("ERP", {}).get("online", False)
    mes_ok = health.get("MES", {}).get("online", False)
    pcs_ok = health.get("PCS", {}).get("online", False)
    icons = {True: "🟢", False: "🔴"}
    st.sidebar.markdown(
        f"**Connected Systems**  \n"
        f"{icons[erp_ok]} ERP &nbsp; {icons[mes_ok]} MES &nbsp; {icons[pcs_ok]} PCS"
    )
except Exception:
    st.sidebar.markdown("**Connected Systems**  \n⚪ ERP &nbsp; ⚪ MES &nbsp; ⚪ PCS")

st.sidebar.markdown("---")

PAGES = {
    "📊 Dashboard": "dashboard",
    "📋 Production Orders": "orders",
    "🔬 Batch Execution": "execution",
    "⚠️ Deviations": "deviations",
    "📜 Audit Trail": "audit_trail",
    "✅ Review & Release": "review",
    "🔌 Integration Status": "integration",
}

selection = st.sidebar.radio("Navigation", list(PAGES.keys()))

st.sidebar.markdown("---")
st.sidebar.caption(
    "Pharma batch execution simulator wired to ERP, MES, and PCS. "
    "Covers order flow, step execution, quality checks, deviations, audit trail, and release review."
)
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reset Demo Data"):
    from pharma.app.utils.persistence import reset_all
    reset_all()
    load_all_demo_scenarios()
    st.sidebar.success("Demo data reset.")
    st.rerun()

# ── Page routing ───────────────────────────────────────────────────────────
page_module = PAGES[selection]

if page_module == "dashboard":
    from pharma.app.pages import dashboard
    dashboard.render()
elif page_module == "orders":
    from pharma.app.pages import orders
    orders.render()
elif page_module == "execution":
    from pharma.app.pages import execution
    execution.render()
elif page_module == "deviations":
    from pharma.app.pages import deviations
    deviations.render()
elif page_module == "audit_trail":
    from pharma.app.pages import audit_trail
    audit_trail.render()
elif page_module == "review":
    from pharma.app.pages import review
    review.render()
elif page_module == "integration":
    from pharma.app.pages import integration
    integration.render()
