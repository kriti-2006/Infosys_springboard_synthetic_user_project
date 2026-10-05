import hmac
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from config import settings


async def require_api_key(x_api_key: str | None = Header(default=None)):
    """Optional auth compatibility: enforced only when API_KEY is set (Milestone 2 had no auth)."""
    if settings.API_KEY and not (x_api_key and hmac.compare_digest(x_api_key, settings.API_KEY)):
        raise HTTPException(401, "invalid or missing API key")


_hits: dict[str, deque] = defaultdict(deque)


async def rate_limit(request: Request):
    """Sliding-window per-client limiter (in-memory; use a shared store such as Redis if you run multiple instances)."""
    limit = settings.RATE_LIMIT_PER_MINUTE
    if limit <= 0:
        return
    now, key = time.monotonic(), request.client.host if request.client else "unknown"
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "rate limit exceeded")
    q.append(now)
