"""
Production Orders Page
Allows creation of simulated ERP production orders, sending them to MES,
and instantiating batches.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from pharma.app.domain.enums import OrderStatus
from pharma.app.services.batch_service import create_batch
from pharma.app.services.order_service import (
    create_order,
    get_all_orders,
    get_order,
    mark_in_execution,
    send_to_mes,
)
from pharma.app.services.recipe_service import get_all_recipes, get_recipe_for_product
from pharma.app.utils.helpers import badge, fmt_dt


def render() -> None:
    st.title("📋 Production Orders")
    st.caption("Simulate ERP production order creation and dispatch to MES.")
    st.markdown("---")

    tab_list, tab_create = st.tabs(["Order List", "Create New Order"])

    # ── Order List ────────────────────────────────────────────────────────────
    with tab_list:
        orders = get_all_orders()
        if not orders:
            st.info("No production orders found. Use the 'Create New Order' tab.")
        else:
            # Filter
            status_filter = st.selectbox(
                "Filter by status",
                ["All"] + [s.value for s in OrderStatus],
                key="order_status_filter",
            )
            filtered = orders if status_filter == "All" else [o for o in orders if o.status.value == status_filter]

            rows = []
            for o in filtered:
                rows.append({
                    "Order ID": o.order_id,
                    "Product": f"{o.product_name} ({o.product_code})",
                    "Qty": f"{o.quantity} {o.unit}",
                    "Due Date": o.due_date,
                    "Site": o.site,
                    "Status": badge(o.status.value),
                    "Batch Ref": o.batch_id_ref or "—",
                    "Created": fmt_dt(o.created_at),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Order Actions")

            order_ids = [o.order_id for o in filtered]
            selected_id = st.selectbox("Select Order", order_ids, key="order_action_select")

            if selected_id:
                selected = get_order(selected_id)
                if selected:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if selected.status == OrderStatus.CREATED:
                            if st.button("📤 Send to MES", key="send_to_mes"):
                                updated = send_to_mes(selected_id, user="planner")
                                if updated:
                                    st.success(f"Order {selected_id} sent to MES.")
                                    st.rerun()
                        else:
                            st.info(f"Status: {badge(selected.status.value)}")

                    with col2:
                        if selected.status == OrderStatus.SENT_TO_MES and not selected.batch_id_ref:
                            recipes = get_all_recipes()
                            recipe_options = {f"{r.name} (v{r.version})": r.recipe_id for r in recipes if r.product_code == selected.product_code}
                            if recipe_options:
                                recipe_label = st.selectbox("Select Recipe", list(recipe_options.keys()), key="recipe_select")
                                recipe_id = recipe_options[recipe_label]
                                if st.button("🧪 Instantiate Batch", key="instantiate_batch"):
                                    batch = create_batch(
                                        order_id=selected_id,
                                        product_code=selected.product_code,
                                        product_name=selected.product_name,
                                        site=selected.site,
                                        quantity=selected.quantity,
                                        unit=selected.unit,
                                        recipe_id=recipe_id,
                                        created_by="mes_operator",
                                    )
                                    mark_in_execution(selected_id, batch.batch_id, user="mes_operator")
                                    st.success(f"Batch {batch.batch_id} created and linked to order {selected_id}.")
                                    st.rerun()
                            else:
                                st.warning(f"No recipe found for product {selected.product_code}.")

                    with col3:
                        if selected.batch_id_ref:
                            st.info(f"Linked Batch: **{selected.batch_id_ref}**")

    # ── Create New Order ──────────────────────────────────────────────────────
    with tab_create:
        st.subheader("New Production Order")
        recipes = get_all_recipes()
        product_options = {f"{r.product_name if hasattr(r, 'product_name') else r.product_code} ({r.product_code})": r.product_code for r in recipes}
        # Derive product names from recipe names
        product_display = {}
        for r in recipes:
            display = f"{r.name.split('–')[0].strip()} ({r.product_code})"
            product_display[display] = r.product_code

        with st.form("create_order_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                product_label = st.selectbox("Product", list(product_display.keys()))
                quantity = st.number_input("Target Quantity", min_value=0.1, value=15.0, step=0.5)
                unit = st.selectbox("Unit", ["kg", "vials", "L", "units"])
                site = st.selectbox("Site", ["Site A – Basel", "Site B – Dublin", "Site C – Singapore"])

            with col_b:
                due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))
                created_by = st.text_input("Created By", value="planner")
                notes = st.text_area("Notes", height=80)

            submitted = st.form_submit_button("Create Order")
            if submitted:
                product_code = product_display[product_label]
                # Derive product name from label
                product_name = product_label.split("(")[0].strip()
                order = create_order(
                    product_code=product_code,
                    product_name=product_name,
                    quantity=quantity,
                    unit=unit,
                    due_date=str(due_date),
                    site=site,
                    created_by=created_by,
                    notes=notes if notes else None,
                )
                st.success(f"Production order **{order.order_id}** created successfully.")
                st.rerun()
