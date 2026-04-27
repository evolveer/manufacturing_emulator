"""
common/auth.py
Shared authentication and authorization utilities.

Provides:
- API key validation decorator for write/control endpoints
- CORS origin helper that reads from environment
"""
import os
import logging
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, '.env'))

logger = logging.getLogger('auth')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_internal_api_key() -> str:
    """Return the expected internal API key from the environment."""
    key = os.environ.get('INTERNAL_API_KEY', '')
    if not key:
        logger.warning(
            "INTERNAL_API_KEY is not set. "
            "All authenticated requests will be rejected."
        )
    return key


def get_cors_origins() -> list:
    """Return the list of allowed CORS origins from the environment."""
    raw = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5000')
    return [o.strip() for o in raw.split(',') if o.strip()]


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def require_api_key(f):
    """
    Decorator that enforces API-key authentication on write/control endpoints.

    The caller must supply the key in one of:
      - Header:  X-API-Key: <key>
      - Header:  Authorization: Bearer <key>

    Internal service-to-service calls (from data_sync, machine_simulator, etc.)
    must include the same key that is stored in INTERNAL_API_KEY.

    Read-only (GET) requests are passed through without a key check so that
    dashboards can still fetch data without credentials.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow unauthenticated GET requests (read-only)
        if request.method == 'GET':
            return f(*args, **kwargs)

        expected_key = _get_internal_api_key()
        if not expected_key:
            logger.error("No INTERNAL_API_KEY configured – rejecting request.")
            return jsonify({'error': 'Service not configured for authentication'}), 503

        # Extract key from headers
        provided_key = request.headers.get('X-API-Key') or ''
        if not provided_key:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                provided_key = auth_header[7:]

        if not provided_key:
            logger.warning(
                "Unauthenticated %s %s from %s",
                request.method, request.path, request.remote_addr
            )
            return jsonify({'error': 'Authentication required. Provide X-API-Key header.'}), 401

        # Constant-time comparison to prevent timing attacks
        import hmac
        if not hmac.compare_digest(provided_key, expected_key):
            logger.warning(
                "Invalid API key on %s %s from %s",
                request.method, request.path, request.remote_addr
            )
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)

    return decorated
