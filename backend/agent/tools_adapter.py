"""
工具适配层

将现有 ToolRegistry 转换为 LangChain Tool 格式
"""

import inspect
import logging

from langchain_core.tools import StructuredTool

from ..tools.registry import tool_registry

logger = logging.getLogger(__name__)


def convert_tools(registry=None) -> list[StructuredTool]:
    """
    将 ToolRegistry 转换为 LangChain Tool 列表

    使用 StructuredTool.from_function 自动从函数签名推断参数 schema，
    确保 LLM 知晓每个工具需要的参数。

    Args:
        registry: ToolRegistry 实例，默认使用全局 tool_registry

    Returns:
        LangChain StructuredTool 列表
    """
    registry = registry or tool_registry
    tools = []

    for name, tool_def in registry._tools.items():
        if inspect.iscoroutinefunction(tool_def.fn):
            tool = StructuredTool.from_function(
                name=name,
                description=tool_def.description,
                coroutine=tool_def.fn,
            )
        else:
            tool = StructuredTool.from_function(
                name=name,
                description=tool_def.description,
                func=tool_def.fn,
            )
        tools.append(tool)
        logger.debug(f"Converted tool: {name}")

    logger.info(f"Converted {len(tools)} tools to LangChain format")
    return tools


def get_tool_descriptions(registry=None) -> str:
    """获取所有工具的描述，用于 prompt 注入"""
    registry = registry or tool_registry
    descriptions = []
    for name, tool_def in registry._tools.items():
        descriptions.append(f"- {name}: {tool_def.description}")
    return "\n".join(descriptions)
