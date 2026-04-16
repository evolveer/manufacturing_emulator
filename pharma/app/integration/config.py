"""
Integration Configuration
Reads system URLs from the shared config.yaml or falls back to environment variables.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pharma.integration.config")

# ── Resolve config.yaml ────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[5]  # manufacturing_emulator/
_CONFIG_PATH = _REPO_ROOT / "config.yaml"


def _load_yaml_config() -> dict:
    try:
        import yaml  # type: ignore
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f)
    except Exception as exc:
        logger.warning("Could not load config.yaml (%s). Using defaults.", exc)
        return {}


_cfg = _load_yaml_config()


def _url(section: str, default_port: int) -> str:
    host = os.environ.get(f"PHARMA_{section.upper()}_HOST") or "localhost"
    port = os.environ.get(f"PHARMA_{section.upper()}_PORT") or str(
        _cfg.get(section, {}).get("port", default_port)
    )
    api_ver = _cfg.get(section, {}).get("api_version", "v1")
    return f"http://{host}:{port}/api/{api_ver}"


ERP_BASE_URL: str = _url("erp", 5001)
MES_BASE_URL: str = _url("mes", 5002)
PCS_BASE_URL: str = _url("pcs", 5003)

# Timeout for HTTP calls (seconds)
HTTP_TIMEOUT: int = int(os.environ.get("PHARMA_INTEGRATION_TIMEOUT", "5"))

# Whether to raise on integration errors or log-and-continue
STRICT_MODE: bool = os.environ.get("PHARMA_INTEGRATION_STRICT", "false").lower() == "true"

logger.info(
    "Integration config loaded: ERP=%s  MES=%s  PCS=%s  timeout=%ds  strict=%s",
    ERP_BASE_URL,
    MES_BASE_URL,
    PCS_BASE_URL,
    HTTP_TIMEOUT,
    STRICT_MODE,
)
