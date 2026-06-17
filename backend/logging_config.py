"""
结构化日志配置

- JSON 格式（生产环境）：含时间、级别、消息、request_id、user_id
- 可读格式（开发环境）：彩色控制台输出
"""

import logging
import sys
from contextvars import ContextVar, Token
from typing import Any

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


class RequestContextFilter(logging.Filter):
    """将 request_id / user_id 注入每条日志记录。"""

    def __init__(self) -> None:
        super().__init__()

    @property
    def request_id(self) -> str:
        return _request_id_var.get()

    @request_id.setter
    def request_id(self, value: str) -> None:
        _request_id_var.set(value)

    @property
    def user_id(self) -> str:
        return _user_id_var.get()

    @user_id.setter
    def user_id(self, value: str) -> None:
        _user_id_var.set(value)

    def set_context(self, request_id: str, user_id: str) -> tuple[Token[str], Token[str]]:
        return (_request_id_var.set(request_id), _user_id_var.set(user_id))

    def reset_context(self, tokens: tuple[Token[str], Token[str]]) -> None:
        request_token, user_token = tokens
        _request_id_var.reset(request_token)
        _user_id_var.reset(user_token)

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()  # type: ignore[attr-defined]
        record.user_id = _user_id_var.get()  # type: ignore[attr-defined]
        return True


# 模块级单例，中间件负责更新其字段
request_filter = RequestContextFilter()


class JsonFormatter(logging.Formatter):
    """将日志记录格式化为单行 JSON，便于日志采集系统解析。"""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry: dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "logger": record.name,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """开发环境可读格式，带颜色。"""

    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = self.formatTime(record, "%H:%M:%S")
        rid = getattr(record, "request_id", "-")
        uid = getattr(record, "user_id", "-")
        prefix = f"{color}{time_str} [{record.levelname:<7}]{self.RESET}"
        ctx = f" rid={rid} uid={uid}" if rid != "-" or uid != "-" else ""
        msg = record.getMessage()
        line = f"{prefix}{ctx} {record.name}: {msg}"
        if record.exc_info and record.exc_info[0] is not None:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(*, level: str = "INFO", fmt: str = "console") -> None:
    """
    初始化全局日志。

    Args:
        level: 日志级别（DEBUG / INFO / WARNING / ERROR）
        fmt: "json" 使用 JSON 格式，其他值使用控制台格式
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 移除已有 handler，避免重复输出
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(request_filter)

    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root.addHandler(handler)

    # 降低第三方库日志噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
