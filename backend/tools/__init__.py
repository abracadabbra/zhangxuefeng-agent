"""
工具注册表 — Function Calling 框架核心

提供装饰器注册工具，管理工具元数据和调度执行
"""

from .registry import register_tool, tool_registry

__all__ = ["tool_registry", "register_tool"]
