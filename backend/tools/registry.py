"""
工具注册表 — 管理工具定义和调度执行

使用装饰器 @register_tool 注册工具函数
"""
import inspect
import json
import time
import logging
from typing import Callable, Any
from dataclasses import dataclass, field

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

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._cache: dict[str, tuple[float, str]] = {}  # key -> (expire_ts, result)

    def register(self, name: str, description: str, parameters: dict[str, Any]):
        """装饰器：注册一个工具函数"""
        def decorator(fn: Callable) -> Callable:
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

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        """调度执行指定工具，返回 JSON 字符串结果（带 TTL 缓存）"""
        tool = self._tools.get(name)
        if not tool:
            return f'{{"error": "Unknown tool: {name}"}}'

        # 检查缓存
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
            result_str = result if isinstance(result, str) else str(result)

            # 写入缓存
            self._cache[key] = (time.time() + CACHE_TTL, result_str)
            return result_str
        except Exception as e:
            return f'{{"error": "Tool execution failed: {str(e)}"}}'

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# 全局单例
tool_registry = ToolRegistry()

# 便捷别名
register_tool = tool_registry.register
