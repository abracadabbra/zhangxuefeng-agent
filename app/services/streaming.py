"""
SSE 流式输出服务

功能：
- 流式调用 LLM API
- 生成 SSE 事件流
- 支持工具调用的流式处理
"""
import json
from typing import AsyncGenerator

import httpx

from app.core.config import get_settings


async def stream_chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.8,
    max_tokens: int = 2000,
) -> AsyncGenerator[dict, None]:
    """
    流式调用 OpenAI Chat Completion API

    Yields:
        dict: 包含 type 和 content 的事件
            - {"type": "text", "content": "..."}
            - {"type": "tool_call", "name": "...", "arguments": {...}}
            - {"type": "done", "usage": {...}}
    """
    settings = get_settings()

    payload = {
        "model": settings.MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            response.raise_for_status()

            current_tool_calls = {}
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                finish_reason = choices[0].get("finish_reason")

                # 处理文本内容
                if "content" in delta and delta["content"]:
                    yield {"type": "text", "content": delta["content"]}

                # 处理工具调用
                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.get("id", ""),
                                "name": "",
                                "arguments": "",
                            }

                        if "function" in tc:
                            func = tc["function"]
                            if "name" in func:
                                current_tool_calls[idx]["name"] = func["name"]
                            if "arguments" in func:
                                current_tool_calls[idx]["arguments"] += func["arguments"]

                # 工具调用完成
                if finish_reason == "tool_calls":
                    for idx, tc in current_tool_calls.items():
                        try:
                            args = json.loads(tc["arguments"])
                        except json.JSONDecodeError:
                            args = {}
                        yield {
                            "type": "tool_call",
                            "id": tc["id"],
                            "name": tc["name"],
                            "arguments": args,
                        }
                    current_tool_calls = {}

                # 正常完成
                if finish_reason == "stop":
                    usage = data.get("usage", {})
                    yield {"type": "done", "usage": usage}


def format_sse_event(event_data: dict) -> str:
    """格式化为 SSE 事件字符串"""
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
