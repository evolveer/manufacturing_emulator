"""
ERP Integration Adapter
Maps pharma domain events to ERP API calls:
  - Register pharma products in ERP product catalogue
  - Register pharma raw materials in ERP inventory
  - Create / update ERP production orders when pharma orders are created
  - Update ERP order status when pharma batch lifecycle changes
  - Consume / return material stock when batch steps execute
  - Sync ERP product list back to pharma for order creation
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseClient
from .config import ERP_BASE_URL

logger = logging.getLogger("pharma.integration.erp")


class ERPClient(BaseClient):
    """Adapter for the ERP emulator REST API (port 5001)."""

    def __init__(self) -> None:
        super().__init__(ERP_BASE_URL, "ERP")

    # ── Products ────────────────────────────────────────────────────────────
    def get_products(self) -> List[Dict]:
        data, status = self._get("/products")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_product_by_code(self, code: str) -> Optional[Dict]:
        data, status = self._get(f"/products/code/{code}")
        if status == 200 and isinstance(data, dict) and "id" in data:
            return data
        return None

    def ensure_product(self, product_code: str, product_name: str, unit: str = "kg") -> Optional[Dict]:
        """Upsert a pharma product in the ERP catalogue."""
        existing = self.get_product_by_code(product_code)
        if existing:
            logger.debug("ERP product already exists: %s", product_code)
            return existing
        payload = {
            "code": product_code,
            "name": product_name,
            "description": f"Pharma product – {product_name}",
            "category": "Pharmaceutical",
            "price": 0.0,
            "stock_quantity": 0.0,
            "min_stock_level": 0.0,
        }
        data, status = self._post("/products", payload)
        if status in (200, 201) and data:
            logger.info("ERP product created: %s (%s)", product_code, product_name)
            return data
        logger.warning("Failed to create ERP product %s: status=%d", product_code, status)
        return None

    def update_product_stock(self, product_code: str, quantity_delta: float) -> bool:
        """Increment (positive) or decrement (negative) ERP product stock."""
        product = self.get_product_by_code(product_code)
        if not product:
            logger.warning("ERP product not found for stock update: %s", product_code)
            return False
        product_id = product["id"]
        new_qty = max(0.0, product.get("stock_quantity", 0.0) + quantity_delta)
        data, status = self._put(f"/products/{product_id}", {"stock_quantity": new_qty})
        if status == 200:
            logger.info("ERP product stock updated: %s → %.2f", product_code, new_qty)
            return True
        return False

    # ── Materials ───────────────────────────────────────────────────────────
    def get_materials(self) -> List[Dict]:
        data, status = self._get("/materials")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_material_by_code(self, code: str) -> Optional[Dict]:
        data, status = self._get(f"/materials/code/{code}")
        if status == 200 and isinstance(data, dict) and "id" in data:
            return data
        return None

    def ensure_material(
        self,
        code: str,
        name: str,
        unit: str = "kg",
        initial_stock: float = 1000.0,
    ) -> Optional[Dict]:
        """Upsert a pharma raw material in ERP inventory."""
        existing = self.get_material_by_code(code)
        if existing:
            return existing
        payload = {
            "code": code,
            "name": name,
            "description": f"Pharma raw material – {name}",
            "unit": unit,
            "cost": 0.0,
            "stock_quantity": initial_stock,
            "min_stock_level": 50.0,
        }
        data, status = self._post("/materials", payload)
        if status in (200, 201) and data:
            logger.info("ERP material created: %s (%s)", code, name)
            return data
        logger.warning("Failed to create ERP material %s: status=%d", code, status)
        return None

    def consume_material(self, material_code: str, quantity: float) -> bool:
        """Deduct consumed material stock in ERP."""
        material = self.get_material_by_code(material_code)
        if not material:
            logger.warning("ERP material not found: %s", material_code)
            return False
        material_id = material["id"]
        payload = {
            "material_id": material_id,
            "quantity": quantity,
            "transaction_type": "consumption",
            "reference": "pharma_batch",
        }
        data, status = self._post("/material-transactions", payload)
        if status in (200, 201):
            logger.info("ERP material consumed: %s qty=%.2f", material_code, quantity)
            return True
        logger.warning("ERP material consume failed: %s status=%d", material_code, status)
        return False

    # ── Production Orders ───────────────────────────────────────────────────
    def get_orders(self) -> List[Dict]:
        data, status = self._get("/orders")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_order_by_number(self, order_number: str) -> Optional[Dict]:
        data, status = self._get(f"/orders/number/{order_number}")
        if status == 200 and isinstance(data, dict) and "id" in data:
            return data
        return None

    def create_production_order(
        self,
        pharma_order_id: str,
        product_code: str,
        product_name: str,
        quantity: float,
        due_date: str,
        site: str,
    ) -> Optional[Dict]:
        """Create a matching ERP production order for a pharma order."""
        # Ensure product exists first
        self.ensure_product(product_code, product_name)

        # Look up ERP product id
        product = self.get_product_by_code(product_code)
        if not product:
            logger.warning("Cannot create ERP order – product not found: %s", product_code)
            return None

        payload = {
            "order_number": pharma_order_id,
            "status": "planned",
            "notes": f"Pharma batch order – site: {site}",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": quantity,
                    "unit_price": 0.0,
                }
            ],
        }
        data, status = self._post("/orders", payload)
        if status in (200, 201) and data:
            logger.info("ERP production order created: %s", pharma_order_id)
            return data
        logger.warning("ERP order creation failed for %s: status=%d data=%s", pharma_order_id, status, data)
        return None

    def update_order_status(self, erp_order_number: str, new_status: str) -> bool:
        """Update the status of an ERP order (e.g. 'in_progress', 'completed')."""
        order = self.get_order_by_number(erp_order_number)
        if not order:
            logger.warning("ERP order not found for status update: %s", erp_order_number)
            return False
        order_id = order["id"]
        data, status = self._put(f"/orders/{order_id}/status", {"status": new_status})
        if status == 200:
            logger.info("ERP order %s status → %s", erp_order_number, new_status)
            return True
        return False

    # ── Production Plans ────────────────────────────────────────────────────
    def create_production_plan(
        self,
        plan_number: str,
        order_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create an ERP production plan linked to a pharma batch."""
        payload = {
            "plan_number": plan_number,
            "status": "planned",
        }
        if order_id:
            payload["order_id"] = order_id
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        data, status = self._post("/production-plans", payload)
        if status in (200, 201) and data:
            logger.info("ERP production plan created: %s", plan_number)
            return data
        logger.warning("ERP production plan creation failed: status=%d", status)
        return None

    def update_production_plan_status(self, plan_number: str, new_status: str) -> bool:
        data, status = self._get(f"/production-plans/number/{plan_number}")
        if status != 200 or not data or "id" not in data:
            return False
        plan_id = data["id"]
        result, s = self._put(f"/production-plans/{plan_id}", {"status": new_status})
        return s == 200
