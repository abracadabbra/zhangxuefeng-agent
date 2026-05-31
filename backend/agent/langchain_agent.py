"""
LangChain Agent 核心模块

支持多步推理、对话记忆、结构化输出
"""
import logging
from typing import AsyncGenerator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from .llm_factory import create_llm
from .tools_adapter import convert_tools
from .prompt import SYSTEM_PROMPT
from .structured_output import RecommendationResult, get_format_instructions
from ..tools.registry import tool_registry
from ..session_store import SessionStore

logger = logging.getLogger(__name__)

# 默认最大迭代次数
MAX_ITERATIONS = 5


class LangChainAgent:
    """
    LangChain Agent 核心类

    支持：
    - 多步工具调用
    - 对话历史管理
    - 流式输出
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        system_prompt: str | None = None,
        skill_path: str | None = None,
        session_store: SessionStore | None = None,
    ):
        self.llm = llm or create_llm()
        self.system_prompt = system_prompt or self._load_skill_prompt(skill_path)
        self.session_store = session_store

        # 转换工具
        self.tools = convert_tools(tool_registry)

        # 创建 ReAct Agent (langgraph)
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )

    def _load_skill_prompt(self, skill_path: str | None = None) -> str:
        """加载 SKILL.md 作为 system prompt"""
        import os
        path = skill_path or os.getenv("SKILL_PATH", "SKILL.md")
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            # 剥离 YAML 前置元数据
            if content.startswith("---"):
                _, _, body = content.partition("---")
                _, _, body = body.partition("---")
                return body.strip()
            return content.strip()
        except FileNotFoundError:
            logger.warning(f"SKILL.md not found at {path}, using built-in prompt")
            return SYSTEM_PROMPT

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
        # 加载对话历史
        chat_history = []
        if self.session_store:
            session = self.session_store.get_or_create(session_id)
            for msg in session.get("history", []):
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

        # 构建输入
        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        # 构建消息列表
        messages = chat_history + [HumanMessage(content=input_text)]

        try:
            # 执行 Agent (langgraph)
            result = await self.agent.ainvoke({"messages": messages})

            # 提取回复
            reply = ""
            tool_calls = []
            for msg in result.get("messages", []):
                if hasattr(msg, "type"):
                    if msg.type == "ai":
                        reply = msg.content or reply
                    elif msg.type == "tool":
                        tool_calls.append({
                            "name": msg.name,
                            "result": msg.content[:500],
                        })

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
        chat_history = []
        if self.session_store:
            session = self.session_store.get_or_create(session_id)
            for msg in session.get("history", []):
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        system_content = f"{self.system_prompt}\n\n{get_format_instructions()}"
        messages = [
            SystemMessage(content=system_content),
            *chat_history,
            HumanMessage(content=input_text),
        ]

        structured_llm = self.llm.with_structured_output(RecommendationResult)

        try:
            result = await structured_llm.ainvoke(messages)

            if self.session_store:
                self.session_store.add_message(session_id, "user", message)
                self.session_store.add_message(
                    session_id, "assistant", result.summary,
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
        # 加载对话历史
        chat_history = []
        if self.session_store:
            session = self.session_store.get_or_create(session_id)
            for msg in session.get("history", []):
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

        # 构建输入
        input_text = message
        if user_context:
            context_str = self._format_user_context(user_context)
            if context_str:
                input_text = f"{context_str}\n\n{message}"

        # 构建消息列表
        messages = chat_history + [HumanMessage(content=input_text)]
        full_reply = ""

        try:
            # 流式执行 Agent (langgraph)
            async for event in self.agent.astream({"messages": messages}):
                # langgraph 返回的是 messages 列表
                if "messages" in event:
                    for msg in event["messages"]:
                        if hasattr(msg, "type"):
                            if msg.type == "ai" and msg.content:
                                full_reply += msg.content
                                yield {"type": "text", "content": msg.content}

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
        if score := user_context.get("分数"):
            parts.append(f"- 考生分数：{score}分")
        if province := user_context.get("省份"):
            parts.append(f"- 所在省份：{province}")
        if category := user_context.get("科类"):
            parts.append(f"- 文理科：{category}")
        if family := user_context.get("家庭条件"):
            parts.append(f"- 家庭条件：{family}")
        if budget := user_context.get("预算"):
            parts.append(f"- 预算范围：{budget}")

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
                tool_calls.append({
                    "name": action.tool,
                    "arguments": action.tool_input,
                    "result": str(observation)[:500],  # 截断过长结果
                })
        return tool_calls
