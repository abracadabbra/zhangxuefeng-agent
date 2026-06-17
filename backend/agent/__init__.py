"""
Agent 核心 — OpenAI API 对接 + Function Calling 调度

提供对话引擎、工具调用循环、流式输出支持
"""

from .core import AgentCore
from .prompt import SYSTEM_PROMPT

# 延迟导入 LangChain Agent，避免强制依赖
try:
    from .langchain_agent import LangChainAgent

    __all__ = ["AgentCore", "SYSTEM_PROMPT", "LangChainAgent"]
except ImportError:
    __all__ = ["AgentCore", "SYSTEM_PROMPT"]
