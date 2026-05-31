"""
API 限流中间件

基于 IP 的滑动窗口限流，默认 60 次/分钟。
Redis 不可用时自动放行。
"""
import logging
import os
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))  # 秒


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的 API 限流中间件"""

    def __init__(self, app, limit: int = RATE_LIMIT, window: int = RATE_WINDOW):
        super().__init__(app)
        self.limit = limit
        self.window = window
        # 内存 fallback: {ip: [timestamp, ...]}
        self._buckets: dict[str, list[float]] = {}

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_bucket(self, ip: str, now: float) -> None:
        cutoff = now - self.window
        if ip in self._buckets:
            self._buckets[ip] = [t for t in self._buckets[ip] if t > cutoff]

    async def dispatch(self, request: Request, call_next) -> Response:
        # 健康检查不计入限流
        if request.url.path in ("/", "/health"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        now = time.time()

        self._clean_bucket(ip, now)

        bucket = self._buckets.setdefault(ip, [])
        if len(bucket) >= self.limit:
            retry_after = int(self.window - (now - bucket[0]))
            return Response(
                content='{"detail":"请求过于频繁，请稍后再试"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        bucket.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(self.limit - len(bucket))
        return response
