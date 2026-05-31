"""LangChain Agent 集成测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.llm_factory import create_llm
from backend.agent.tools_adapter import convert_tools, get_tool_descriptions
from backend.tools.registry import ToolRegistry

# 导入 LangChain Agent 模块
from backend.agent import langchain_agent


class TestLLMFactory:
    """LLM 工厂测试"""

    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
    def test_create_openai_llm(self):
        """测试创建 OpenAI LLM"""
        llm = create_llm(provider="openai", model="gpt-4o-mini")
        assert llm is not None
        assert hasattr(llm, "invoke")

    @patch.dict("os.environ", {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"})
    def test_create_anthropic_llm(self):
        """测试创建 Anthropic LLM"""
        llm = create_llm(provider="anthropic", model="claude-3-5-sonnet-20241022")
        assert llm is not None
        assert hasattr(llm, "invoke")

    def test_create_llm_invalid_provider(self):
        """测试无效 provider"""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm(provider="invalid")

    @patch.dict("os.environ", {}, clear=True)
    def test_create_llm_missing_api_key(self):
        """测试缺少 API Key"""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            create_llm(provider="openai")


class TestToolsAdapter:
    """工具适配层测试"""

    def test_convert_tools(self):
        """测试工具转换"""
        # 创建一个测试用的 registry
        registry = ToolRegistry()

        @registry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
        )
        def test_fn(query: str) -> str:
            return f"Result: {query}"

        tools = convert_tools(registry)
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A test tool"

    def test_convert_async_tools(self):
        """测试异步工具转换"""
        registry = ToolRegistry()

        @registry.register(
            name="async_tool",
            description="An async tool",
            parameters={"type": "object", "properties": {}},
        )
        async def async_fn(query: str) -> str:
            return f"Async result: {query}"

        tools = convert_tools(registry)
        assert len(tools) == 1
        assert tools[0].name == "async_tool"

    def test_get_tool_descriptions(self):
        """测试获取工具描述"""
        registry = ToolRegistry()

        @registry.register(
            name="tool1",
            description="First tool",
            parameters={"type": "object", "properties": {}},
        )
        def fn1() -> str:
            return "result"

        @registry.register(
            name="tool2",
            description="Second tool",
            parameters={"type": "object", "properties": {}},
        )
        def fn2() -> str:
            return "result"

        desc = get_tool_descriptions(registry)
        assert "tool1: First tool" in desc
        assert "tool2: Second tool" in desc

    def test_convert_empty_registry(self):
        """测试空 registry 转换"""
        registry = ToolRegistry()
        tools = convert_tools(registry)
        assert len(tools) == 0


class TestLangChainAgent:
    """LangChain Agent 核心测试"""

    @patch.object(langchain_agent, "create_llm")
    @patch.object(langchain_agent, "convert_tools")
    def test_agent_initialization(self, mock_convert_tools, mock_create_llm):
        """测试 Agent 初始化"""
        from backend.agent.langchain_agent import LangChainAgent

        # Mock LLM 和工具
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        mock_convert_tools.return_value = []

        agent = LangChainAgent(llm=mock_llm)
        assert agent.llm == mock_llm
        assert agent.tools == []

    @patch.object(langchain_agent, "create_llm")
    @patch.object(langchain_agent, "convert_tools")
    def test_agent_with_custom_prompt(self, mock_convert_tools, mock_create_llm):
        """测试自定义 system prompt"""
        from backend.agent.langchain_agent import LangChainAgent

        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        mock_convert_tools.return_value = []

        custom_prompt = "You are a custom AI assistant."
        agent = LangChainAgent(llm=mock_llm, system_prompt=custom_prompt)
        assert agent.system_prompt == custom_prompt

    @patch.object(langchain_agent, "create_llm")
    @patch.object(langchain_agent, "convert_tools")
    def test_agent_with_session_store(self, mock_convert_tools, mock_create_llm):
        """测试带 session_store 的 Agent"""
        from backend.agent.langchain_agent import LangChainAgent

        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        mock_convert_tools.return_value = []

        mock_store = MagicMock()
        agent = LangChainAgent(llm=mock_llm, session_store=mock_store)
        assert agent.session_store == mock_store
