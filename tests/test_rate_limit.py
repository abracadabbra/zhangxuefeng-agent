import httpx
import pytest
from fastapi import FastAPI

from backend.middleware.rate_limit import RateLimitMiddleware, RateLimitPolicy


def _build_app() -> FastAPI:
    app = FastAPI()
    policies = {
        "chat": RateLimitPolicy("chat", limit=1, window=60),
        "recommend": RateLimitPolicy("recommend", limit=1, window=60),
        "export": RateLimitPolicy("export", limit=1, window=60),
        "default": RateLimitPolicy("default", limit=2, window=60),
    }
    app.add_middleware(RateLimitMiddleware, policies=policies)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/chat")
    async def chat():
        return {"ok": True}

    @app.post("/recommend")
    async def recommend():
        return {"ok": True}

    @app.api_route("/chat", methods=["OPTIONS"])
    async def chat_options():
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_rate_limit_is_scoped_by_route_family():
    transport = httpx.ASGITransport(app=_build_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_chat = await client.post("/chat")
        second_chat = await client.post("/chat")
        first_recommend = await client.post("/recommend")

    assert first_chat.status_code == 200
    assert first_chat.headers["X-RateLimit-Scope"] == "chat"
    assert first_chat.headers["X-RateLimit-Remaining"] == "0"

    assert second_chat.status_code == 429
    assert second_chat.headers["X-RateLimit-Scope"] == "chat"
    assert second_chat.headers["X-RateLimit-Remaining"] == "0"
    assert int(second_chat.headers["Retry-After"]) >= 1
    assert int(second_chat.headers["X-RateLimit-Reset"]) >= 1
    assert second_chat.headers["X-Request-ID"]
    assert float(second_chat.headers["X-Process-Time-Ms"]) >= 0

    assert first_recommend.status_code == 200
    assert first_recommend.headers["X-RateLimit-Scope"] == "recommend"
    assert first_recommend.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_rate_limit_429_preserves_request_id_header():
    transport = httpx.ASGITransport(app=_build_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/chat")
        limited = await client.post("/chat", headers={"X-Request-ID": "rate-limit-req-001"})

    assert limited.status_code == 429
    assert limited.headers["X-Request-ID"] == "rate-limit-req-001"
    assert float(limited.headers["X-Process-Time-Ms"]) >= 0


@pytest.mark.asyncio
async def test_rate_limit_skips_health_and_options_requests():
    transport = httpx.ASGITransport(app=_build_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/health")
        options = await client.options("/chat")
        chat = await client.post("/chat")

    assert health.status_code == 200
    assert "X-RateLimit-Scope" not in health.headers

    assert options.status_code == 200
    assert "X-RateLimit-Scope" not in options.headers

    assert chat.status_code == 200
    assert chat.headers["X-RateLimit-Scope"] == "chat"
