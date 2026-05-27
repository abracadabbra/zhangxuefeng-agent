"""LLM 服务 — 封装 OpenAI API 调用 + 用量追踪"""

import logging

import httpx

from app.core.config import get_settings
from app.core.metrics import metrics

logger = logging.getLogger(__name__)


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.8,
    max_tokens: int = 2000,
) -> dict:
    """调用 OpenAI Chat Completion API

    Returns:
        dict: API 响应 JSON（含 usage 字段）
    """
    settings = get_settings()

    payload = {
        "model": settings.MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        metrics.record_llm_error()
        logger.error("LLM 调用失败: %s", e)
        raise

    # 记录 token 用量
    usage = data.get("usage", {})
    if usage:
        metrics.record_llm_call(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", settings.MODEL),
        )

    return data
