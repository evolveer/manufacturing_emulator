"""
echotrace.integration — HTTP client shim for log_audit_trail.

Sends audit records to the EchoTrace microservice via its REST API
(POST /api/v1/audit-trail) instead of writing directly to the database.

This fixes issue #4: the previous implementation bypassed the EchoTrace
microservice by writing directly to audit.db using its own SQLAlchemy
engine, violating service isolation.

The function signature is backward-compatible with every existing call site.
Extra kwargs are silently absorbed so future call sites with additional
fields do not break.
"""
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env')

logger = logging.getLogger("echotrace")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_echotrace_url() -> str:
    """Return the EchoTrace API base URL from environment or config."""
    url = os.environ.get('ECHOTRACE_URL', 'http://localhost:5004')
    return url.rstrip('/')


def _get_api_key() -> str:
    """Return the internal API key for authenticated requests."""
    return os.environ.get('INTERNAL_API_KEY', '')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_audit_trail(
    user_id=None,
    username=None,
    action="UPDATE",
    entity_type="Unknown",
    entity_id=None,
    source_system=None,
    entity_name=None,
    old_value=None,
    new_value=None,
    changes=None,
    **kwargs,  # absorb any extra keyword args from future call sites
):
    """
    Send one audit-trail record to the EchoTrace microservice via HTTP.

    Parameters
    ----------
    user_id       : int   — numeric user identifier (0 = system)
    username      : str   — human-readable user name
    action        : str   — CREATE | UPDATE | DELETE
    entity_type   : str   — e.g. "Order", "WorkOrder", "Material"
    entity_id     : int   — primary key of the affected record
    source_system : str   — e.g. "ERP", "MES"
    entity_name   : str   — human-readable name of the entity
    old_value     : dict  — state before the change (optional)
    new_value     : dict  — state after the change (optional)
    changes       : dict  — field-level diff (optional)
    """
    try:
        import requests  # lazy import to avoid hard dependency at module load

        payload = {
            'user_id': user_id if user_id is not None else 0,
            'username': username or 'system',
            'action': action,
            'entity_type': entity_type,
            'entity_id': str(entity_id) if entity_id is not None else '0',
            'source_system': source_system or 'unknown',
        }
        if entity_name is not None:
            payload['entity_name'] = entity_name
        if old_value is not None:
            payload['old_value'] = (
                json.dumps(old_value, default=str)
                if not isinstance(old_value, str)
                else old_value
            )
        if new_value is not None:
            payload['new_value'] = (
                json.dumps(new_value, default=str)
                if not isinstance(new_value, str)
                else new_value
            )
        if changes is not None:
            payload['changes'] = (
                json.dumps(changes, default=str)
                if not isinstance(changes, str)
                else changes
            )

        base_url = _get_echotrace_url()
        api_key = _get_api_key()
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

        response = requests.post(
            f"{base_url}/api/v1/audit-trail",
            json=payload,
            headers=headers,
            timeout=3,
        )

        if response.status_code not in (200, 201):
            logger.warning(
                "EchoTrace audit POST returned %s: %s",
                response.status_code, response.text[:200]
            )

    except Exception as exc:
        # Audit logging must never crash the calling service
        logger.warning("echotrace: failed to send audit record: %s", exc)


def get_audit_trail(
    entity_type=None,
    entity_id=None,
    source_system=None,
    limit=200,
):
    """
    Query audit records from the EchoTrace microservice.
    All filters are optional.  Returns a list of dicts, newest first.
    """
    try:
        import requests  # lazy import

        params = {'limit': limit, 'order_direction': 'desc'}
        if entity_type:
            params['entity_type'] = entity_type
        if entity_id is not None:
            params['entity_id'] = str(entity_id)
        if source_system:
            params['source_system'] = source_system

        base_url = _get_echotrace_url()
        response = requests.get(
            f"{base_url}/api/v1/audit-trail/search",
            params=params,
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            # The search endpoint returns {'results': [...], 'total': N}
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            if isinstance(data, list):
                return data
        else:
            logger.warning(
                "EchoTrace audit GET returned %s: %s",
                response.status_code, response.text[:200]
            )
    except Exception as exc:
        logger.warning("echotrace: failed to retrieve audit records: %s", exc)

    return []
