"""
工具注册表 — 管理工具定义和调度执行

使用装饰器 @register_tool 注册工具函数
"""

import inspect
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 分钟


@dataclass(frozen=True)
class ToolDef:
    """工具定义：名称、描述、参数 schema、执行函数"""

    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable


class ToolRegistry:
    """工具注册表 — 存储和调度所有已注册工具"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._cache: dict[str, tuple[float, Any]] = {}  # key -> (expire_ts, result)

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """装饰器：注册一个工具函数"""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = ToolDef(
                name=name,
                description=description,
                parameters=parameters,
                fn=fn,
            )
            return fn

        return decorator

    def get_tool(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def get_all_definitions(self) -> list[dict[str, Any]]:
        """返回所有工具的 OpenAI function calling 格式定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def _cache_key(self, name: str, arguments: dict[str, Any]) -> str:
        """生成缓存 key：func_name + sorted args"""
        sorted_args = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        return f"{name}:{sorted_args}"

    async def dispatch_raw(self, name: str, arguments: dict[str, Any]) -> Any:
        """调度执行指定工具，返回原始结构化结果（带 TTL 缓存）"""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}

        key = self._cache_key(name, arguments)
        if key in self._cache:
            expire_ts, cached = self._cache[key]
            if time.time() < expire_ts:
                logger.debug(f"Cache hit: {name}")
                return cached
            else:
                del self._cache[key]

        try:
            if inspect.iscoroutinefunction(tool.fn):
                result = await tool.fn(**arguments)
            else:
                result = tool.fn(**arguments)

            self._cache[key] = (time.time() + CACHE_TTL, result)
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        """调度执行指定工具，返回字符串结果（Agent tool message 边界）"""
        result = await self.dispatch_raw(name, arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# 全局单例
tool_registry = ToolRegistry()

# 便捷别名
register_tool = tool_registry.register
