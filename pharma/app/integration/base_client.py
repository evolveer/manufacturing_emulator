"""
Base HTTP Client
Shared request helpers, health-check, and structured error handling for all
integration adapters.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import requests

from .config import HTTP_TIMEOUT, STRICT_MODE

logger = logging.getLogger("pharma.integration.base")


class IntegrationError(Exception):
    """Raised when an upstream system returns an unexpected error."""


class BaseClient:
    """Thin wrapper around requests with logging and error handling."""

    def __init__(self, base_url: str, system_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.system_name = system_name

    # ── Health ─────────────────────────────────────────────────────────────
    def is_online(self) -> bool:
        """Return True if the upstream system responds to /status."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=2)
            return r.status_code < 500
        except Exception:
            return False

    def health(self) -> Dict[str, Any]:
        """Return a health dict: {online, url, system}."""
        online = self.is_online()
        return {"system": self.system_name, "url": self.base_url, "online": online}

    # ── HTTP helpers ────────────────────────────────────────────────────────
    def _get(self, path: str, params: Optional[Dict] = None) -> Tuple[Optional[Dict], int]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            logger.debug("GET %s → %d", url, r.status_code)
            return self._parse(r), r.status_code
        except requests.RequestException as exc:
            return self._handle_exc(exc, "GET", url)

    def _post(self, path: str, payload: Dict) -> Tuple[Optional[Dict], int]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
            logger.debug("POST %s → %d", url, r.status_code)
            return self._parse(r), r.status_code
        except requests.RequestException as exc:
            return self._handle_exc(exc, "POST", url)

    def _put(self, path: str, payload: Dict) -> Tuple[Optional[Dict], int]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            r = requests.put(url, json=payload, timeout=HTTP_TIMEOUT)
            logger.debug("PUT %s → %d", url, r.status_code)
            return self._parse(r), r.status_code
        except requests.RequestException as exc:
            return self._handle_exc(exc, "PUT", url)

    # ── Internals ───────────────────────────────────────────────────────────
    @staticmethod
    def _parse(r: requests.Response) -> Optional[Dict]:
        try:
            return r.json()
        except Exception:
            return {"raw": r.text, "status_code": r.status_code}

    def _handle_exc(self, exc: Exception, method: str, url: str) -> Tuple[None, int]:
        msg = f"{self.system_name} {method} {url} failed: {exc}"
        if STRICT_MODE:
            raise IntegrationError(msg) from exc
        logger.warning(msg)
        return None, 0
