"""
工具适配层

将现有 ToolRegistry 转换为 LangChain Tool 格式
"""
import asyncio
import inspect
import logging
from langchain_core.tools import Tool

from ..tools.registry import tool_registry

logger = logging.getLogger(__name__)


def convert_tools(registry=None) -> list[Tool]:
    """
    将 ToolRegistry 转换为 LangChain Tool 列表

    Args:
        registry: ToolRegistry 实例，默认使用全局 tool_registry

    Returns:
        LangChain Tool 列表
    """
    registry = registry or tool_registry
    tools = []

    for name, tool_def in registry._tools.items():
        # 处理异步函数
        if inspect.iscoroutinefunction(tool_def.fn):
            # 包装异步函数为同步
            def make_sync(fn):
                def sync_wrapper(*args, **kwargs):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环已在运行，使用 asyncio.ensure_future
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            future = pool.submit(asyncio.run, fn(*args, **kwargs))
                            return future.result()
                    else:
                        return asyncio.run(fn(*args, **kwargs))
                return sync_wrapper
            func = make_sync(tool_def.fn)
        else:
            func = tool_def.fn

        # 创建 LangChain Tool
        tool = Tool(
            name=name,
            description=tool_def.description,
            func=func,
            coroutine=tool_def.fn if inspect.iscoroutinefunction(tool_def.fn) else None,
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
