"""
MES Integration Adapter
Maps pharma domain events to MES API calls:
  - Create MES work orders when pharma batches are instantiated
  - Update MES work order status as batch steps progress
  - Push quality check results from step completions
  - Log material consumption transactions per step
  - Sync machine assignments and production counts
  - Pull downtime events and surface them as potential deviations
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseClient
from .config import MES_BASE_URL

logger = logging.getLogger("pharma.integration.mes")


class MESClient(BaseClient):
    """Adapter for the MES emulator REST API (port 5002)."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        super().__init__(base_url or MES_BASE_URL, "MES")

    # ── Work Orders ─────────────────────────────────────────────────────────
    def get_work_orders(self) -> List[Dict]:
        data, status = self._get("/work-orders")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_work_order_by_number(self, number: str) -> Optional[Dict]:
        data, status = self._get(f"/work-orders/number/{number}")
        if status == 200 and isinstance(data, dict) and "id" in data:
            return data
        return None

    def create_work_order(
        self,
        batch_id: str,
        product_id: int,
        quantity: float,
        production_plan_id: int,
        machine_id: Optional[int] = None,
    ) -> Optional[Dict]:
        """Create a MES work order for a pharma batch."""
        payload = {
            "work_order_number": batch_id,
            "production_plan_id": production_plan_id,
            "product_id": product_id,
            "quantity": int(quantity),
            "status": "planned",
        }
        if machine_id:
            payload["machine_id"] = machine_id
        data, status = self._post("/work-orders", payload)
        if status in (200, 201) and data:
            logger.info("MES work order created: %s", batch_id)
            return data
        logger.warning("MES work order creation failed for %s: status=%d data=%s", batch_id, status, data)
        return None

    def update_work_order_status(self, work_order_number: str, new_status: str) -> bool:
        """Update MES work order status (planned/in_progress/completed/on_hold)."""
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            logger.warning("MES work order not found: %s", work_order_number)
            return False
        wo_id = wo["id"]
        data, status = self._put(f"/work-orders/{wo_id}/status", {"status": new_status})
        if status == 200:
            logger.info("MES work order %s status → %s", work_order_number, new_status)
            return True
        return False

    def get_active_work_orders(self) -> List[Dict]:
        data, status = self._get("/work-orders/active")
        if status == 200 and isinstance(data, list):
            return data
        return []

    # ── Quality Checks ──────────────────────────────────────────────────────
    def get_quality_checks(self) -> List[Dict]:
        data, status = self._get("/quality-checks")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def create_quality_check(
        self,
        work_order_number: str,
        check_type: str,
        parameter_name: str,
        actual_value: float,
        min_value: Optional[float],
        max_value: Optional[float],
        passed: bool,
        notes: str = "",
    ) -> Optional[Dict]:
        """Push a quality check result to MES from a pharma parameter capture."""
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            logger.warning("MES work order not found for quality check: %s", work_order_number)
            return None
        wo_id = wo["id"]
        # MES QualityCheck model uses 'parameter' and 'value' (not parameter_name/actual_value/result)
        payload = {
            "work_order_id": wo_id,
            "parameter": parameter_name,
            "value": float(actual_value) if actual_value is not None else 0.0,
            "min_value": min_value,
            "max_value": max_value,
            "status": "pass" if passed else "fail",
            "notes": f"[{check_type}] {notes}" if check_type else notes,
        }
        data, status = self._post("/quality-checks", payload)
        if status in (200, 201) and data:
            logger.info(
                "MES quality check created: WO=%s param=%s result=%s",
                work_order_number, parameter_name, "pass" if passed else "fail",
            )
            return data
        logger.warning("MES quality check failed: status=%d", status)
        return None

    def get_quality_summary(self, work_order_number: str) -> Optional[Dict]:
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return None
        data, status = self._get(f"/work-orders/{wo['id']}/quality-summary")
        return data if status == 200 else None

    # ── Material Tracking ────────────────────────────────────────────────────
    def allocate_materials(self, work_order_number: str, materials: List[Dict]) -> bool:
        """Allocate materials to a MES work order."""
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return False
        wo_id = wo["id"]
        data, status = self._post(f"/work-orders/{wo_id}/allocate-materials", {"materials": materials})
        if status in (200, 201):
            logger.info("MES materials allocated to WO %s", work_order_number)
            return True
        return False

    def consume_materials(self, work_order_number: str, materials: List[Dict]) -> bool:
        """Record material consumption for a MES work order step."""
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return False
        wo_id = wo["id"]
        data, status = self._post(f"/work-orders/{wo_id}/consume-materials", {"materials": materials})
        if status in (200, 201):
            logger.info("MES materials consumed for WO %s: %s", work_order_number, materials)
            return True
        return False

    def get_material_transactions(self, work_order_number: str) -> List[Dict]:
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return []
        data, status = self._get(f"/work-orders/{wo['id']}/material-transactions")
        return data if status == 200 and isinstance(data, list) else []

    # ── Production Counts ────────────────────────────────────────────────────
    def increment_production_count(
        self,
        work_order_number: str,
        good: int = 0,
        reject: int = 0,
        rework: int = 0,
    ) -> bool:
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return False
        wo_id = wo["id"]
        data, status = self._post(
            f"/work-orders/{wo_id}/increment-count",
            {"good_count": good, "reject_count": reject, "rework_count": rework},
        )
        return status in (200, 201)

    def get_production_summary(self, work_order_number: str) -> Optional[Dict]:
        wo = self.get_work_order_by_number(work_order_number)
        if not wo:
            return None
        data, status = self._get(f"/work-orders/{wo['id']}/production-summary")
        return data if status == 200 else None

    # ── Machines ─────────────────────────────────────────────────────────────
    def get_machines(self) -> List[Dict]:
        data, status = self._get("/machines")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_available_machines(self) -> List[Dict]:
        data, status = self._get("/machines/available")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_machine_by_id(self, machine_id: int) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}")
        return data if status == 200 else None

    # ── Downtime ─────────────────────────────────────────────────────────────
    def get_active_downtimes(self) -> List[Dict]:
        data, status = self._get("/downtimes/active")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_downtimes_for_machine(self, machine_id: int) -> List[Dict]:
        data, status = self._get(f"/machines/{machine_id}/downtimes")
        return data if status == 200 and isinstance(data, list) else []

    # ── Production Plans ─────────────────────────────────────────────────────
    def get_production_plans(self) -> List[Dict]:
        data, status = self._get("/production-plans")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def create_production_plan(self, plan_number: str, order_id: Optional[int] = None) -> Optional[Dict]:
        payload = {"plan_number": plan_number, "status": "planned"}
        if order_id:
            payload["order_id"] = order_id
        data, status = self._post("/production-plans", payload)
        if status in (200, 201) and data:
            logger.info("MES production plan created: %s", plan_number)
            return data
        return None
