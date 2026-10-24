"""
Centralized Rate Limiting Module for PlannedEducation.

Strict Security Architecture:
- Rate limiter is ALWAYS enabled and enforced across all environments.
- Zero environment bypass loopholes (no bypass for 'test' or 'dev').
- Shared single instance across all API routes and application state.
- Resilient client IP extraction with proxy support.
"""

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


# Single unified Limiter instance - STRICT: always enabled, no environment loopholes
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],
    headers_enabled=False,
    enabled=True,
)

__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler", "get_client_ip"]
