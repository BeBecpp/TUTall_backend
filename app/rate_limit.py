import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings

_request_buckets: dict[str, Deque[float]] = defaultdict(deque)
_MAX_BUCKETS = 10_000
_EXEMPT_PATHS = {"/", "/health", "/api/meta", "/docs", "/redoc", "/openapi.json"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _prune_bucket(bucket: Deque[float], now: float, window: int) -> None:
    while bucket and now - bucket[0] > window:
        bucket.popleft()


def _trim_buckets() -> None:
    if len(_request_buckets) <= _MAX_BUCKETS:
        return
    stale_keys = list(_request_buckets.keys())[: len(_request_buckets) - _MAX_BUCKETS]
    for key in stale_keys:
        _request_buckets.pop(key, None)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()
        limit = settings.rate_limit_per_minute
        window = 60
        now = time.time()
        ip = _client_ip(request)
        bucket = _request_buckets[ip]

        _prune_bucket(bucket, now, window)

        if len(bucket) >= limit:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Rate limit exceeded. Please try again in a minute.",
                        "request_id": request_id,
                    }
                },
            )

        bucket.append(now)
        _trim_buckets()
        return await call_next(request)
