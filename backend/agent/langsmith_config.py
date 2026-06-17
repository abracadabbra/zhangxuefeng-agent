"""
LangSmith 配置模块

支持链路追踪、成本监控、质量评估
"""

import logging
import os

logger = logging.getLogger(__name__)


def setup_langsmith():
    """
    配置 LangSmith 追踪

    环境变量：
    - LANGCHAIN_TRACING_V2: 启用追踪 (true/false)
    - LANGCHAIN_API_KEY: LangSmith API Key
    - LANGCHAIN_PROJECT: 项目名称
    - LANGCHAIN_ENDPOINT: API 端点 (默认 https://api.smith.langchain.com)
    """
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if not tracing_enabled:
        logger.info("LangSmith tracing is disabled")
        return

    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        logger.warning("LANGCHAIN_API_KEY not set, tracing will not work")
        return

    # 设置环境变量（LangChain 自动读取）
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

    project = os.getenv("LANGCHAIN_PROJECT", "zhangxuefeng-agent")
    os.environ["LANGCHAIN_PROJECT"] = project

    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    logger.info(f"LangSmith tracing enabled: project={project}, endpoint={endpoint}")


def get_trace_url(run_id: str) -> str:
    """获取追踪链接"""
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    return f"{endpoint}/runs/{run_id}"
