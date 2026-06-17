"""
共享依赖：Agent 实例管理、SessionStore、配置常量
"""

import logging

from backend.agent.core import AgentCore
from backend.config import get_settings
from backend.session_store import SessionStore
from backend.soul_query import SoulQueryEngine

logger = logging.getLogger(__name__)

settings = get_settings()

# ============== 向后兼容常量 ==============
OPENAI_API_KEY = settings.openai_api_key
OPENAI_BASE_URL = settings.openai_base_url
MODEL = settings.effective_model
USE_LANGCHAIN = settings.use_langchain

# ============== Singletons ==============
session_store = SessionStore()
soul_engine = SoulQueryEngine()

_agent = None


def get_agent():
    """获取 Agent 实例（根据 USE_LANGCHAIN 切换）"""
    global _agent
    if _agent is None:
        if settings.use_langchain:
            from backend.agent.langchain_agent import LangChainAgent

            _agent = LangChainAgent(session_store=session_store)
            logger.info("Using LangChain Agent")
        else:
            _agent = AgentCore(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.effective_model,
            )
            logger.info("Using AgentCore")
    return _agent
