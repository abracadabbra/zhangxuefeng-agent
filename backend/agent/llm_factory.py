"""
LLM 工厂模块

支持通过环境变量切换 LLM provider（OpenAI/Anthropic）
"""

import logging
import os

from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_PROVIDER = "openai"
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
}


def create_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.8,
    max_tokens: int = 2000,
) -> BaseChatModel:
    """
    根据 provider 创建 LLM 实例

    环境变量：
    - LLM_PROVIDER: "openai" 或 "anthropic"
    - LLM_MODEL: 模型名称
    - OPENAI_API_KEY: OpenAI API Key
    - ANTHROPIC_API_KEY: Anthropic API Key
    """
    provider = provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
    model = model or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODELS.get(provider)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")
        llm = ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        logger.info(f"Created OpenAI LLM: {model}")
        return llm

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created Anthropic LLM: {model}")
        return llm

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: openai, anthropic")
