"""
Integration Configuration
Reads system URLs from the shared config.yaml or falls back to environment variables.

L3 fix: adds three layers of URL resolution (highest priority first):
  1. Full URL env-var override  e.g. PHARMA_ERP_URL=http://erp:5001/api/v1
     → ideal for Docker Compose where service names replace localhost
  2. Host/port env-var overrides  PHARMA_ERP_HOST + PHARMA_ERP_PORT
     → useful for partial overrides (e.g. only changing the host)
  3. config.yaml values (fallback, default: localhost + configured port)

Also fixes the fragile parents[N] repo-root detection by walking up until
config.yaml is found, rather than assuming a fixed directory depth.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pharma.integration.config")


# ── Repo-root detection ────────────────────────────────────────────────────
def _find_repo_root() -> Optional[Path]:
    """Walk up from this file until we find config.yaml (repo root marker).

    L3 fix: replaces the fragile parents[5] hard-coded depth with a search
    that works regardless of where the pharma module is located within the
    repository.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):  # guard against infinite loops
        if (current / "config.yaml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


_REPO_ROOT = _find_repo_root()
_CONFIG_PATH = (_REPO_ROOT / "config.yaml") if _REPO_ROOT else None


def _load_yaml_config() -> dict:
    if _CONFIG_PATH is None:
        logger.warning("config.yaml not found in any parent directory. Using defaults.")
        return {}
    try:
        import yaml  # type: ignore
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f)
    except Exception as exc:
        logger.warning("Could not load config.yaml (%s). Using defaults.", exc)
        return {}


_cfg = _load_yaml_config()


def _resolve_url(section: str, default_port: int) -> str:
    """Resolve the base URL for a downstream service.

    Resolution order (highest priority first):
      1. PHARMA_{SECTION}_URL  — full URL, e.g. http://erp:5001/api/v1
         Supports Docker Compose service names and any custom base path.
      2. PHARMA_{SECTION}_HOST + PHARMA_{SECTION}_PORT
         Builds http://{host}:{port}/api/{api_version}.
      3. config.yaml pharma.integration.{section}_url (if present)
      4. config.yaml {section}.host + {section}.port (bind addr → localhost)
      5. http://localhost:{default_port}/api/v1
    """
    section_upper = section.upper()

    # Layer 1: full URL override
    full_url_env = os.environ.get(f"PHARMA_{section_upper}_URL")
    if full_url_env:
        logger.debug("Using env PHARMA_%s_URL = %s", section_upper, full_url_env)
        return full_url_env.rstrip("/")

    # Layer 2: host/port env-var overrides
    host_env = os.environ.get(f"PHARMA_{section_upper}_HOST")
    port_env = os.environ.get(f"PHARMA_{section_upper}_PORT")

    # Layer 3: config.yaml pharma.integration block
    pharma_integration = _cfg.get("pharma", {}).get("integration", {})
    cfg_full_url = pharma_integration.get(f"{section}_url")
    if cfg_full_url and not host_env and not port_env:
        logger.debug("Using config.yaml pharma.integration.%s_url = %s", section, cfg_full_url)
        return cfg_full_url.rstrip("/")

    # Layer 4: config.yaml {section} block
    section_cfg = _cfg.get(section, {})
    host = host_env or section_cfg.get("host", "localhost")
    # Translate bind address to loopback for outbound client connections
    if host in ("0.0.0.0", "::"):
        host = "localhost"
    port = port_env or str(section_cfg.get("port", default_port))
    api_ver = section_cfg.get("api_version", "v1")

    url = f"http://{host}:{port}/api/{api_ver}"
    logger.debug("Resolved %s URL from config: %s", section_upper, url)
    return url


# ── Public constants ───────────────────────────────────────────────────────
ERP_BASE_URL: str = _resolve_url("erp", 5001)
MES_BASE_URL: str = _resolve_url("mes", 5002)
PCS_BASE_URL: str = _resolve_url("pcs", 5003)

# Timeout for HTTP calls (seconds)
HTTP_TIMEOUT: int = int(
    os.environ.get("PHARMA_INTEGRATION_TIMEOUT")
    or _cfg.get("pharma", {}).get("integration", {}).get("timeout_seconds", 5)
)

# Whether to raise on integration errors or log-and-continue
STRICT_MODE: bool = (
    os.environ.get("PHARMA_INTEGRATION_STRICT", "").lower() == "true"
    or _cfg.get("pharma", {}).get("integration", {}).get("strict_mode", False)
)

logger.info(
    "Integration config loaded: ERP=%s  MES=%s  PCS=%s  timeout=%ds  strict=%s",
    ERP_BASE_URL,
    MES_BASE_URL,
    PCS_BASE_URL,
    HTTP_TIMEOUT,
    STRICT_MODE,
)
