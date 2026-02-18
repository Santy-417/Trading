from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, accounting for proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_client_ip, default_limits=["100/minute"])

# Stricter limit for auth-related endpoints
auth_limiter = limiter.limit("10/minute")

# Stricter limit for trading operations
trading_limiter = limiter.limit("30/minute")
