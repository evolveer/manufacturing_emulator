"""
Order Service
Manages production order lifecycle: creation, status transitions, and retrieval.
"""

from __future__ import annotations

from typing import List, Optional

from ..domain.enums import OrderStatus
from ..domain.models import ProductionOrder
from ..utils.persistence import get_by_id, load_all, upsert
from . import audit_service

ENTITY = "orders"


def create_order(
    product_code: str,
    product_name: str,
    quantity: float,
    unit: str,
    due_date: str,
    site: str,
    created_by: str = "planner",
    notes: Optional[str] = None,
) -> ProductionOrder:
    order = ProductionOrder(
        product_code=product_code,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        due_date=due_date,
        site=site,
        created_by=created_by,
        notes=notes,
    )
    upsert(ENTITY, ProductionOrder, order, "order_id")
    audit_service.log_event(
        user=created_by,
        action="batch created",
        entity_type="ProductionOrder",
        entity_id=order.order_id,
        new_value=OrderStatus.CREATED.value,
        comment=f"Order for {product_name} ({product_code}), qty {quantity} {unit}",
    )
    return order


def send_to_mes(order_id: str, user: str = "planner") -> Optional[ProductionOrder]:
    order = get_by_id(ENTITY, ProductionOrder, "order_id", order_id)
    if not order or order.status != OrderStatus.CREATED:
        return None
    old = order.status.value
    order.status = OrderStatus.SENT_TO_MES
    upsert(ENTITY, ProductionOrder, order, "order_id")
    audit_service.log_event(
        user=user,
        action="disposition changed",
        entity_type="ProductionOrder",
        entity_id=order_id,
        old_value=old,
        new_value=order.status.value,
    )
    return order


def mark_in_execution(order_id: str, batch_id: str, user: str = "system") -> Optional[ProductionOrder]:
    order = get_by_id(ENTITY, ProductionOrder, "order_id", order_id)
    if not order:
        return None
    old = order.status.value
    order.status = OrderStatus.IN_EXECUTION
    order.batch_id_ref = batch_id
    upsert(ENTITY, ProductionOrder, order, "order_id")
    audit_service.log_event(
        user=user,
        action="disposition changed",
        entity_type="ProductionOrder",
        entity_id=order_id,
        old_value=old,
        new_value=order.status.value,
        comment=f"Batch {batch_id} created",
    )
    return order


def complete_order(order_id: str, user: str = "system") -> Optional[ProductionOrder]:
    order = get_by_id(ENTITY, ProductionOrder, "order_id", order_id)
    if not order:
        return None
    old = order.status.value
    order.status = OrderStatus.COMPLETED
    upsert(ENTITY, ProductionOrder, order, "order_id")
    audit_service.log_event(
        user=user,
        action="disposition changed",
        entity_type="ProductionOrder",
        entity_id=order_id,
        old_value=old,
        new_value=order.status.value,
    )
    return order


def get_all_orders() -> List[ProductionOrder]:
    return load_all(ENTITY, ProductionOrder)


def get_order(order_id: str) -> Optional[ProductionOrder]:
    return get_by_id(ENTITY, ProductionOrder, "order_id", order_id)
