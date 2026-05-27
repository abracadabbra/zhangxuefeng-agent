"""
Agent 核心引擎 — OpenAI API 对接 + Function Calling 调度

职责：
1. 调用 OpenAI Chat Completions API
2. 处理 tool_calls 响应
3. 多轮工具调用循环（最多 3 轮）
4. 流式输出支持
"""
import json
import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from .prompt import SYSTEM_PROMPT
from ..tools.registry import tool_registry
from ..tools.definitions import TOOLS

logger = logging.getLogger(__name__)

# 最大工具调用轮次
MAX_TOOL_ROUNDS = 5


class AgentCore:
    """张雪峰 AI Agent 核心引擎"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _build_system_prompt(self, user_context: dict | None = None) -> str:
        """构建系统提示词，注入用户上下文"""
        prompt = SYSTEM_PROMPT

        if user_context:
            ctx_parts = []
            if score := user_context.get("分数"):
                ctx_parts.append(f"- 考生分数：{score}分")
            if province := user_context.get("省份"):
                ctx_parts.append(f"- 所在省份：{province}")
            if category := user_context.get("科类"):
                ctx_parts.append(f"- 文理科：{category}")
            if family := user_context.get("家庭条件"):
                ctx_parts.append(f"- 家庭条件：{family}")
            if budget := user_context.get("预算"):
                ctx_parts.append(f"- 预算范围：{budget}")

            if ctx_parts:
                prompt += "\n\n## 当前用户背景\n" + "\n".join(ctx_parts)

        return prompt

    async def chat(
        self,
        messages: list[dict],
        user_context: dict | None = None,
        temperature: float = 0.8,
        max_tokens: int = 2000,
    ) -> dict:
        """
        非流式对话 — 支持多轮工具调用

        返回：{"reply": str, "tool_calls": list, "usage": dict}
        """
        system_prompt = self._build_system_prompt(user_context)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        all_tool_calls = []

        for round_idx in range(MAX_TOOL_ROUNDS):
            response: ChatCompletion = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=TOOLS if TOOLS else None,
                tool_choice="auto" if TOOLS else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            choice = response.choices[0]
            message = choice.message

            # 无工具调用，直接返回
            if not message.tool_calls:
                return {
                    "reply": message.content or "",
                    "tool_calls": all_tool_calls,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    } if response.usage else None,
                }

            # 有工具调用，执行并继续
            full_messages.append(message.model_dump())

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                logger.info(f"Tool call: {func_name}({func_args})")
                result = await tool_registry.dispatch(func_name, func_args)

                all_tool_calls.append({
                    "id": tool_call.id,
                    "name": func_name,
                    "arguments": func_args,
                    "result": result,
                })

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # 超过最大轮次，返回当前回复
        logger.warning(f"Tool call loop exceeded {MAX_TOOL_ROUNDS} rounds")
        return {
            "reply": message.content or "抱歉，处理过程中遇到了问题，请重试。",
            "tool_calls": all_tool_calls,
            "usage": None,
        }

    async def chat_stream(
        self,
        messages: list[dict],
        user_context: dict | None = None,
        temperature: float = 0.8,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[dict, None]:
        """
        流式对话 — 支持多轮工具调用

        产出事件：
        - {"type": "text", "content": "..."}：文本片段
        - {"type": "tool_call", "name": "...", "arguments": {...}}：工具调用
        - {"type": "tool_result", "name": "...", "result": "..."}：工具结果
        - {"type": "done", "usage": {...}}：完成
        """
        system_prompt = self._build_system_prompt(user_context)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        for round_idx in range(MAX_TOOL_ROUNDS):
            # 调试：记录 API 调用
            logger.info(f"=== API Call Round {round_idx + 1} ===")
            logger.info(f"Messages count: {len(full_messages)}")

            # 打印完整的消息结构（用于调试）
            import json
            for i, msg in enumerate(full_messages):
                logger.info(f"  msg[{i}]: role={msg.get('role')}")
                if msg.get('role') == 'system':
                    logger.info(f"    content_len={len(msg.get('content', ''))}")
                elif msg.get('role') == 'assistant' and 'tool_calls' in msg:
                    logger.info(f"    tool_calls_count={len(msg.get('tool_calls', []))}")
                elif msg.get('role') == 'tool':
                    logger.info(f"    tool_call_id={msg.get('tool_call_id')}, content_len={len(str(msg.get('content', '')))}")

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=TOOLS if TOOLS else None,
                tool_choice="auto" if TOOLS else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            collected_content = ""
            collected_tool_calls: list[dict] = []
            usage_info = None

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

                # 文本内容
                if delta and delta.content:
                    collected_content += delta.content
                    yield {"type": "text", "content": delta.content}

                # 工具调用增量
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        while len(collected_tool_calls) <= idx:
                            collected_tool_calls.append({
                                "id": "",
                                "name": "",
                                "arguments": "",
                            })
                        if tc_delta.id:
                            collected_tool_calls[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                collected_tool_calls[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                collected_tool_calls[idx]["arguments"] += tc_delta.function.arguments

                # 使用统计
                if chunk.usage:
                    usage_info = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

            # 无工具调用，结束
            if not collected_tool_calls:
                yield {"type": "done", "usage": usage_info}
                return

            # 执行工具调用
            assistant_msg = {"role": "assistant", "content": collected_content or None, "tool_calls": []}
            tool_messages = []

            for tc in collected_tool_calls:
                func_name = tc["name"]
                # 跳过空的工具调用
                if not func_name:
                    continue

                try:
                    func_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    func_args = {}

                yield {"type": "tool_call", "name": func_name, "arguments": func_args}

                result = await tool_registry.dispatch(func_name, func_args)
                yield {"type": "tool_result", "name": func_name, "result": result}

                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": func_name, "arguments": tc["arguments"] or "{}"},
                })

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # 先添加 assistant 消息，再添加 tool 消息
            full_messages.append(assistant_msg)
            full_messages.extend(tool_messages)

            # 调试：打印发送给 API 的消息结构
            logger.info(f"Round {round_idx + 1}: Sending {len(full_messages)} messages to API")
            for i, msg in enumerate(full_messages[-5:]):
                msg_idx = len(full_messages) - 5 + i
                logger.info(f"  Message {msg_idx}: role={msg.get('role')}, has_tool_calls={'tool_calls' in msg}, has_tool_call_id={'tool_call_id' in msg}")
                if msg.get('role') == 'tool':
                    logger.info(f"    tool_call_id={msg.get('tool_call_id')}, content_len={len(str(msg.get('content', '')))}")

        # 超过最大轮次，强制生成最终回复（不带工具）
        logger.warning(f"Tool call loop exceeded {MAX_TOOL_ROUNDS} rounds, forcing final response")
        final_response = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages + [{"role": "system", "content": "你已经收集了足够的数据，请基于已有信息直接回复用户，不要再调用任何工具。"}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in final_response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield {"type": "text", "content": delta.content}
        yield {"type": "done", "usage": None}
