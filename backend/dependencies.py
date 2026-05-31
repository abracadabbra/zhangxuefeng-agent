"""
共享依赖：Agent 实例管理、SessionStore、配置常量
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

from backend.agent.core import AgentCore
from backend.session_store import SessionStore
from backend.soul_query import SoulQueryEngine

# ============== Config ==============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL", "gpt-4o-mini")
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "false").lower() == "true"

# ============== Singletons ==============
session_store = SessionStore()
soul_engine = SoulQueryEngine()

_agent = None


def get_agent():
    """获取 Agent 实例（根据 USE_LANGCHAIN 切换）"""
    global _agent
    if _agent is None:
        if USE_LANGCHAIN:
            from backend.agent.langchain_agent import LangChainAgent

            _agent = LangChainAgent(session_store=session_store)
            logger.info("Using LangChain Agent")
        else:
            _agent = AgentCore(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                model=MODEL,
            )
            logger.info("Using AgentCore")
    return _agent
