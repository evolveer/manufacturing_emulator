"""
PCS Integration Adapter
Maps pharma domain events to PCS API calls:
  - Read live machine sensor data to populate pharma process parameters
  - Read machine parameters (temperature, pressure, etc.) for step validation
  - Start / stop machines when batch steps begin / end
  - Pull active alarms and surface them as potential deviations
  - Read machine state and uptime for dashboard health panels
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseClient
from .config import PCS_BASE_URL

logger = logging.getLogger("pharma.integration.pcs")


class PCSClient(BaseClient):
    """Adapter for the PCS emulator REST API (port 5003)."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        super().__init__(base_url or PCS_BASE_URL, "PCS")

    # ── Machines ─────────────────────────────────────────────────────────────
    def get_all_machines_status(self) -> List[Dict]:
        """Return list of machine status dicts.
        PCS /machines/status returns a dict keyed by machine_id (e.g. {1: {...}, 2: {...}}).
        We normalise it to a list and inject the 'id' key so callers can use m['id'].
        """
        data, status = self._get("/machines/status")
        if status != 200 or not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            result = []
            for machine_id, info in data.items():
                entry = dict(info) if isinstance(info, dict) else {}
                entry.setdefault("id", int(machine_id))
                result.append(entry)
            return result
        return []

    def ensure_machine(self, machine_id: int) -> bool:
        """Create a PCS machine simulator entry if it doesn't already exist.
        PCS machines are in-memory only and must be registered before start/stop/sensor calls.
        """
        # Check if already registered
        existing = self.get_all_machines_status()
        if any(int(m.get("id", -1)) == machine_id for m in existing):
            return True  # already exists
        data, status = self._post("/machines", {"machine_id": machine_id})
        if status in (200, 201):
            logger.info("PCS machine %d registered", machine_id)
            return True
        logger.warning("PCS machine registration failed: machine_id=%d status=%d", machine_id, status)
        return False

    def get_machine_state(self, machine_id: int) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}/state")
        return data if status == 200 else None

    def get_machine_uptime(self, machine_id: int) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}/uptime")
        return data if status == 200 else None

    def start_machine(self, machine_id: int, work_order_id: Optional[int] = None) -> bool:
        """Start a PCS machine. work_order_id is required by PCS and must match the MES work order."""
        payload: Dict[str, Any] = {}
        if work_order_id is not None:
            payload["work_order_id"] = work_order_id
        data, status = self._post(f"/machines/{machine_id}/start", payload)
        if status in (200, 201):
            logger.info("PCS machine %d started (work_order_id=%s)", machine_id, work_order_id)
            return True
        logger.warning(
            "PCS machine start failed: machine_id=%d work_order_id=%s status=%d data=%s",
            machine_id, work_order_id, status, data,
        )
        return False

    def stop_machine(self, machine_id: int) -> bool:
        data, status = self._post(f"/machines/{machine_id}/stop", {})
        if status in (200, 201):
            logger.info("PCS machine %d stopped", machine_id)
            return True
        return False

    # ── Parameters ───────────────────────────────────────────────────────────
    def get_machine_parameters(self, machine_id: int) -> List[Dict]:
        data, status = self._get(f"/machines/{machine_id}/parameters")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_parameter(self, machine_id: int, parameter_name: str) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}/parameters/{parameter_name}")
        return data if status == 200 else None

    def set_parameter(self, machine_id: int, parameter_name: str, value: float) -> bool:
        data, status = self._post(
            f"/machines/{machine_id}/set-parameter",
            {"parameter_name": parameter_name, "value": value},
        )
        if status in (200, 201):
            logger.info("PCS parameter set: machine=%d %s=%s", machine_id, parameter_name, value)
            return True
        return False

    def get_all_parameters(self) -> List[Dict]:
        data, status = self._get("/parameters")
        if status == 200 and isinstance(data, list):
            return data
        return []

    # ── Sensor Data ───────────────────────────────────────────────────────────
    def get_latest_sensor_data(self, machine_id: int) -> List[Dict]:
        """Return the most recent sensor readings for a machine."""
        data, status = self._get(f"/machines/{machine_id}/sensors")
        if status == 200 and isinstance(data, list):
            return data
        if status == 200 and isinstance(data, dict):
            return [data]
        return []

    def get_sensor_range(
        self,
        machine_id: int,
        sensor_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Dict]:
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        data, status = self._get(f"/machines/{machine_id}/sensors/{sensor_name}/range", params)
        return data if status == 200 and isinstance(data, list) else []

    def get_sensor_statistics(self, machine_id: int, sensor_name: str) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}/sensors/{sensor_name}/statistics")
        return data if status == 200 else None

    # ── Alarms ────────────────────────────────────────────────────────────────
    def get_all_alarms(self) -> List[Dict]:
        data, status = self._get("/alarms")
        if status == 200 and isinstance(data, list):
            return data
        return []

    def get_alarms_for_machine(self, machine_id: int) -> List[Dict]:
        data, status = self._get(f"/machines/{machine_id}/alarms")
        return data if status == 200 and isinstance(data, list) else []

    def get_active_alarms(self) -> List[Dict]:
        """Return all unacknowledged / unresolved alarms."""
        all_alarms = self.get_all_alarms()
        return [a for a in all_alarms if a.get("status") not in ("resolved", "acknowledged")]

    def acknowledge_alarm(self, alarm_id: int) -> bool:
        data, status = self._post(f"/alarms/{alarm_id}/acknowledge", {})
        return status in (200, 201)

    def resolve_alarm(self, alarm_id: int) -> bool:
        data, status = self._post(f"/alarms/{alarm_id}/resolve", {})
        return status in (200, 201)

    # ── Cycles ────────────────────────────────────────────────────────────────
    def get_cycle_statistics(self, machine_id: int) -> Optional[Dict]:
        data, status = self._get(f"/machines/{machine_id}/cycle-statistics")
        return data if status == 200 else None

    def get_cycles_for_machine(self, machine_id: int) -> List[Dict]:
        data, status = self._get(f"/machines/{machine_id}/cycles")
        return data if status == 200 and isinstance(data, list) else []
