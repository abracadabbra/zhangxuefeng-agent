"""
工具注册表 — 管理工具定义和调度执行

使用装饰器 @register_tool 注册工具函数
"""
import inspect
from typing import Callable, Any
from dataclasses import dataclass, field


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

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        """调度执行指定工具，返回 JSON 字符串结果"""
        tool = self._tools.get(name)
        if not tool:
            return f'{{"error": "Unknown tool: {name}"}}'

        try:
            if inspect.iscoroutinefunction(tool.fn):
                result = await tool.fn(**arguments)
            else:
                result = tool.fn(**arguments)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f'{{"error": "Tool execution failed: {str(e)}"}}'

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# 全局单例
tool_registry = ToolRegistry()

# 便捷别名
register_tool = tool_registry.register
