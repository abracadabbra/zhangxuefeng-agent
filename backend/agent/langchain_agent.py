"""
LangChain Agent 核心模块

支持多步推理、对话记忆、结构化输出
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from ..session_store import SessionStore
from ..tools.registry import tool_registry
from .llm_factory import create_llm
from .prompt import SYSTEM_PROMPT
from .structured_output import RecommendationResult, get_recommendation_instructions
from .tools_adapter import convert_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5

# 记忆配置
KEEP_RECENT_ROUNDS = 10  # 保留最近 N 轮原文（每轮 = 1 user + 1 assistant）
MAX_TOKEN_LIMIT = 2000  # 超出此 token 数时触发摘要

SUMMARY_PROMPT = (
    "请将以下对话历史压缩为简洁的摘要，保留关键信息"
    "（用户需求、已给出的建议、重要数据）。\n"
    "只输出摘要内容，不要添加额外说明。\n\n"
    "对话历史：\n{history}"
)


def _estimate_tokens(text: str) -> int:
    """粗略估算中文文本 token 数（约 1.5 字/token）"""
    return max(1, len(text) // 2)


def _message_text(content: object) -> str:
    """Normalize LangChain message content into plain text for storage/counting."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


class LangChainAgent:
    """
    LangChain Agent 核心类

    支持：
    - 多步工具调用
    - 对话记忆（前10轮保留原文，超出自动摘要）
    - 流式输出
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        system_prompt: str | None = None,
        skill_path: str | None = None,
        session_store: SessionStore | None = None,
        max_token_limit: int = MAX_TOKEN_LIMIT,
        keep_recent_rounds: int = KEEP_RECENT_ROUNDS,
    ):
        self.llm = llm or create_llm()
        self.system_prompt = system_prompt or self._load_skill_prompt(skill_path)
        self.session_store = session_store
        self.max_token_limit = max_token_limit
        self.keep_recent_rounds = keep_recent_rounds

        # 转换工具
        self.tools = convert_tools(tool_registry)

        # 创建 LangChain Agent
        self.agent: Any = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

    def _load_skill_prompt(self, skill_path: str | None = None) -> str:
        """加载 SKILL.md 作为 system prompt"""
        import os

        path = skill_path or os.getenv("SKILL_PATH", "SKILL.md")
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            if content.startswith("---"):
                _, _, body = content.partition("---")
                _, _, body = body.partition("---")
                return body.strip()
            return content.strip()
        except FileNotFoundError:
            logger.warning(f"SKILL.md not found at {path}, using built-in prompt")
            return SYSTEM_PROMPT

    def _load_chat_history(self, session_id: str) -> list[HumanMessage | AIMessage]:
        """从 session_store 加载对话历史为 LangChain 消息列表"""
        if not self.session_store:
            return []
        session = self.session_store.get_or_create(session_id)
        history: list[HumanMessage | AIMessage] = []
        for msg in session.get("history", []):
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history.append(AIMessage(content=msg["content"]))
        return history

    async def _summarize_history(self, messages: list[HumanMessage | AIMessage]) -> str:
        """调用 LLM 将消息列表压缩为摘要"""
        history_text = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}：{_message_text(m.content)}"
            for m in messages
        )
        prompt = SUMMARY_PROMPT.format(history=history_text)
        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            summary = _message_text(result.content).strip()
            logger.info(f"Summarized {len(messages)} messages into {len(summary)} chars")
            return summary
        except Exception as e:
            logger.error(f"Failed to summarize history: {e}")
            return ""

    async def _build_memory_messages(self, session_id: str) -> list[BaseMessage]:
        """
        构建带记忆的消息列表。

        策略：前 keep_recent_rounds 轮保留原文，超出部分自动摘要。
        摘要作为 SystemMessage 放在最前面。
        """
        history = self._load_chat_history(session_id)
        if not history:
            return []

        keep_count = self.keep_recent_rounds * 2  # 每轮 2 条消息
        if len(history) <= keep_count:
            return list(history)

        older_messages = history[:-keep_count]
        recent_messages = history[-keep_count:]

        total_tokens = sum(_estimate_tokens(_message_text(m.content)) for m in older_messages)
        if total_tokens <= self.max_token_limit:
            return list(history)

        summary = await self._summarize_history(older_messages)
        if not summary:
            return list(recent_messages)

        return [SystemMessage(content=f"[历史对话摘要]\n{summary}"), *recent_messages]

    async def chat(
        self,
        message: str,
        session_id: str,
        user_context: dict | None = None,
    ) -> dict:
        """
        处理用户消息

        Args:
            message: 用户消息
            session_id: 会话 ID
            user_context: 用户上下文（分数、省份等）

        Returns:
            {"reply": str, "tool_calls": list}
        """
        chat_history = await self._build_memory_messages(session_id)

        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        messages = chat_history + [HumanMessage(content=input_text)]

        try:
            # 执行 Agent (langgraph)
            result = await self.agent.ainvoke({"messages": messages})

            # 提取回复（跳过含 tool_calls 的中间 AI 消息，取最终内容）
            reply = ""
            tool_calls = []
            for msg in result.get("messages", []):
                if hasattr(msg, "type"):
                    if msg.type == "ai" and not getattr(msg, "tool_calls", None):
                        reply = _message_text(msg.content) or reply
                    elif msg.type == "tool":
                        tool_calls.append(
                            {
                                "name": msg.name,
                                "result": _message_text(msg.content)[:500],
                            }
                        )

            # 保存到会话历史
            if self.session_store:
                self.session_store.add_message(session_id, "user", message)
                self.session_store.add_message(session_id, "assistant", reply)

            return {
                "reply": reply,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "reply": f"抱歉，处理过程中出现了错误：{type(e).__name__}",
                "tool_calls": [],
            }

    async def chat_structured(
        self,
        message: str,
        session_id: str,
        user_context: dict | None = None,
    ) -> RecommendationResult:
        """
        结构化输出模式：返回 RecommendationResult 对象

        使用 LLM 的 with_structured_output 能力，直接返回解析好的 Pydantic 对象。
        """
        chat_history = await self._build_memory_messages(session_id)

        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        system_content = f"{self.system_prompt}\n\n{get_recommendation_instructions()}"
        messages = [
            SystemMessage(content=system_content),
            *chat_history,
            HumanMessage(content=input_text),
        ]

        structured_llm = self.llm.with_structured_output(RecommendationResult)

        try:
            raw_result = await structured_llm.ainvoke(messages)
            if isinstance(raw_result, RecommendationResult):
                result = raw_result
            else:
                if isinstance(raw_result, BaseModel):
                    raw_result = raw_result.model_dump()
                result = RecommendationResult.model_validate(raw_result)

            if self.session_store:
                self.session_store.add_message(session_id, "user", message)
                self.session_store.add_message(
                    session_id,
                    "assistant",
                    result.summary,
                )

            return result

        except Exception as e:
            logger.error(f"Structured output failed: {e}")
            return RecommendationResult(
                recommendations=[],
                summary=f"抱歉，结构化推荐生成失败：{type(e).__name__}",
            )

    async def chat_stream(
        self,
        message: str,
        session_id: str,
        user_context: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        流式处理用户消息

        产出事件：
        - {"type": "text", "content": "..."}：文本片段
        - {"type": "tool_call", "name": "...", "arguments": {...}}：工具调用
        - {"type": "tool_result", "name": "...", "result": "..."}：工具结果
        - {"type": "done"}：完成
        """
        chat_history = await self._build_memory_messages(session_id)

        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        messages = chat_history + [HumanMessage(content=input_text)]
        full_reply = ""
        input_count = len(messages)

        try:
            # 流式执行 Agent (langgraph)
            # 用 stream_mode="values" 确保 event 包含完整的 state（含 messages）
            # values 模式下每次 event 携带全部 state，需跳过输入消息，只处理新增的 AI 消息
            async for event in self.agent.astream(
                {"messages": messages}, stream_mode="values"
            ):
                if "messages" in event:
                    msgs = event["messages"]
                    for msg in msgs[input_count:]:
                        if hasattr(msg, "type"):
                            if msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                                content = _message_text(msg.content)
                                if not content or not content.strip():
                                    continue
                                content = content.lstrip("\n")
                                full_reply += content
                                yield {"type": "text", "content": content}
                    input_count = len(msgs)

            # 保存到会话历史
            if self.session_store:
                self.session_store.add_message(session_id, "user", message)
                self.session_store.add_message(session_id, "assistant", full_reply)

            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Agent stream failed: {e}")
            yield {"type": "text", "content": f"\n\n处理出错：{type(e).__name__}"}
            yield {"type": "done"}

    def _format_user_context(self, user_context: dict) -> str:
        """格式化用户上下文"""
        parts = []
        context_fields = [
            ("分数", "考生分数", "分"),
            ("省份", "所在省份", ""),
            ("科类", "文理/选科", ""),
            ("家庭条件", "家庭条件", ""),
            ("目标城市", "目标城市", ""),
            ("风险偏好", "风险偏好", ""),
            ("职业方向", "职业方向", ""),
            ("省份批次", "省份批次", ""),
            ("选科限制", "选科限制", ""),
            ("位次", "省内位次", ""),
            ("家庭预算", "家庭预算", ""),
            ("地域偏好", "地域偏好", ""),
            ("城市层级", "城市层级偏好", ""),
            ("职业偏好权重", "职业偏好权重", ""),
        ]
        for key, label, suffix in context_fields:
            if value := user_context.get(key):
                parts.append(f"- {label}：{value}{suffix}")

        if parts:
            return "## 当前用户背景\n" + "\n".join(parts)
        return ""

    def _extract_tool_calls(self, result: dict) -> list[dict]:
        """从 Agent 结果中提取工具调用记录"""
        tool_calls = []
        # AgentExecutor 的中间步骤包含工具调用信息
        for step in result.get("intermediate_steps", []):
            if len(step) >= 2:
                action, observation = step
                tool_calls.append(
                    {
                        "name": action.tool,
                        "arguments": action.tool_input,
                        "result": str(observation)[:500],  # 截断过长结果
                    }
                )
        return tool_calls
