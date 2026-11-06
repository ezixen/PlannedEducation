"""
Centralized Rate Limiting Module for PlannedEducation.

- Production/staging/development: slowapi always enabled (F-027).
- Test only: limiter disabled so the full pytest suite is not blocked by
  shared TestClient IP (`testclient`) hitting login/register ceilings.
"""

import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_client_ip(request) -> str:
    """
    Extract client IP for rate limiting with fallback.
    Prevents NoneType issues in testing or reverse proxy environments.
    """
    ip = get_remote_address(request)
    return ip if ip else "127.0.0.1"


_env = (os.getenv("PLANNED_EDUCATION_ENV") or "").lower()
_limiter_enabled = _env != "test"

# Single unified Limiter instance — disabled only for pytest (shared client IP).
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],
    headers_enabled=False,
    enabled=_limiter_enabled,
)

__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler", "get_client_ip"]
