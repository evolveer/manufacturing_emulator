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

# Sidebar navigation
st.sidebar.title("⚗️ Pharma Batch Simulator")
st.sidebar.markdown("---")

PAGES = {
    "📊 Dashboard": "dashboard",
    "📋 Production Orders": "orders",
    "🔬 Batch Execution": "execution",
    "⚠️ Deviations": "deviations",
    "📜 Audit Trail": "audit_trail",
    "✅ Review & Release": "review",
}

selection = st.sidebar.radio("Navigation", list(PAGES.keys()))

st.sidebar.markdown("---")
st.sidebar.caption("Simulated pharma batch execution workflow covering MES order flow, step execution, audit trail, deviations, and release review in a regulated manufacturing context.")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reset Demo Data"):
    from pharma.app.utils.persistence import reset_all
    reset_all()
    load_all_demo_scenarios()
    st.sidebar.success("Demo data reset.")
    st.rerun()

# Route to page
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
