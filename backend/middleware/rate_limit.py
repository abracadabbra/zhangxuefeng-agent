"""
API 限流中间件

基于 IP 的滑动窗口限流，默认 60 次/分钟。
Redis 不可用时自动放行。
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))  # 秒


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    limit: int
    window: int


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid integer env %s=%r, using %s", name, os.getenv(name), default)
        return default


def _default_policies(
    limit: int = RATE_LIMIT,
    window: int = RATE_WINDOW,
) -> dict[str, RateLimitPolicy]:
    return {
        "chat": RateLimitPolicy(
            "chat",
            _env_int("RATE_LIMIT_CHAT", limit),
            _env_int("RATE_WINDOW_CHAT", window),
        ),
        "recommend": RateLimitPolicy(
            "recommend",
            _env_int("RATE_LIMIT_RECOMMEND", limit),
            _env_int("RATE_WINDOW_RECOMMEND", window),
        ),
        "export": RateLimitPolicy(
            "export",
            _env_int("RATE_LIMIT_EXPORT", limit),
            _env_int("RATE_WINDOW_EXPORT", window),
        ),
        "default": RateLimitPolicy("default", limit, window),
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的 API 限流中间件"""

    def __init__(
        self,
        app,
        limit: int = RATE_LIMIT,
        window: int = RATE_WINDOW,
        policies: dict[str, RateLimitPolicy] | None = None,
    ):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.policies = policies or _default_policies(limit, window)
        # 内存 fallback: {ip: [timestamp, ...]}
        self._buckets: dict[str, list[float]] = {}

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_policy(self, path: str) -> RateLimitPolicy:
        if path == "/chat" or path.startswith("/api/chat"):
            return self.policies["chat"]
        if path == "/recommend" or path.startswith("/api/recommend"):
            return self.policies["recommend"]
        if path.endswith("/export") or path.endswith("/export/pdf"):
            return self.policies["export"]
        return self.policies["default"]

    def _bucket_key(self, ip: str, policy: RateLimitPolicy) -> str:
        return f"{ip}:{policy.scope}"

    def _clean_bucket(self, key: str, now: float, policy: RateLimitPolicy) -> None:
        cutoff = now - policy.window
        if key in self._buckets:
            self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        # 健康检查和 CORS 预检不计入限流
        if request.method == "OPTIONS" or request.url.path in ("/", "/health"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        policy = self._get_policy(request.url.path)
        key = self._bucket_key(ip, policy)
        now = time.time()

        self._clean_bucket(key, now, policy)

        bucket = self._buckets.setdefault(key, [])
        reset_after = int(policy.window - (now - bucket[0])) if bucket else policy.window
        if len(bucket) >= policy.limit:
            retry_after = max(reset_after, 1)
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "rate limit exceeded scope=%s path=%s ip=%s limit=%s window=%s",
                policy.scope,
                request.url.path,
                ip,
                policy.limit,
                policy.window,
            )
            return Response(
                content='{"detail":"请求过于频繁，请稍后再试"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(policy.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                    "X-RateLimit-Scope": policy.scope,
                    "X-Request-ID": request_id,
                    "X-Process-Time-Ms": f"{duration_ms:.2f}",
                },
            )

        bucket.append(now)
        remaining = max(policy.limit - len(bucket), 0)
        reset_after = max(int(policy.window - (now - bucket[0])), 0)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(policy.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_after)
        response.headers["X-RateLimit-Scope"] = policy.scope
        return response
