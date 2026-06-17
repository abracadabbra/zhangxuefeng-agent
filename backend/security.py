"""
安全工具模块 — 输入验证、XSS 防护、敏感信息脱敏、请求日志
"""

import html
import logging
import re
import uuid
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("security")

# ============== 常量 ==============

MAX_MESSAGE_LENGTH = 1000
MAX_CONTEXT_VALUE_LENGTH = 200
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_SENSITIVE_PATTERNS = [
    (re.compile(r"(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+"), r"\1****"),
    (
        re.compile(r"\b(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
        r"\1****",
    ),
    (
        re.compile(
            r'(["\']?(?:password|passwd|secret|token|api[_-]?key)["\']?\s*:\s*)'
            r'(["\']?)[^,}"\'\s]+(["\']?)',
            re.IGNORECASE,
        ),
        r"\1\2****\3",
    ),
    (
        re.compile(r"(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[^&\s]+", re.IGNORECASE),
        r"\1=****",
    ),
    (
        re.compile(r"((?:password|passwd|secret|token|api[_-]?key)=)[^&\s]+", re.IGNORECASE),
        r"\1****",
    ),
    (re.compile(r"(\b1[3-9]\d)\d{4}(\d{4}\b)"), r"\1****\2"),
    (re.compile(r"([\w.+-]+)@([\w.-]+\.[A-Za-z]{2,})"), r"****@\2"),
]

# ============== 输入验证 ==============


def validate_message(message: str) -> str:
    """验证并清理用户消息"""
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    sanitized = sanitize_input(message)
    if len(sanitized) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"消息长度不能超过 {MAX_MESSAGE_LENGTH} 个字符",
        )
    return sanitized


def validate_session_id(session_id: str | None) -> str:
    """验证 session_id 格式，无效则生成新的"""
    if session_id is None:
        return str(uuid.uuid4())
    if not UUID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="无效的会话 ID 格式")
    return session_id


def validate_user_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """验证并清理用户上下文字段"""
    if context is None:
        return None

    allowed_keys = {
        "分数",
        "省份",
        "科类",
        "家庭条件",
        "目标城市",
        "风险偏好",
        "职业方向",
        "省份批次",
        "选科限制",
        "位次",
        "家庭预算",
        "地域偏好",
        "城市层级",
        "职业偏好权重",
        "score",
        "province",
        "subject",
        "family_background",
        "target_city",
        "risk_tolerance",
        "career_goal",
        "admission_batch",
        "subject_requirements",
        "rank",
        "family_budget",
        "region_preference",
        "city_tier",
        "career_preference_weight",
    }

    cleaned: dict[str, Any] = {}
    for key, value in context.items():
        if key not in allowed_keys:
            continue
        if isinstance(value, str):
            value = sanitize_input(value)
            if len(value) > MAX_CONTEXT_VALUE_LENGTH:
                continue
        cleaned[key] = value

    return cleaned if cleaned else None


# ============== XSS / 输入清理 ==============


def sanitize_input(text: str) -> str:
    """转义 HTML 特殊字符，防止 XSS"""
    return html.escape(text, quote=True)


# ============== 敏感信息脱敏 ==============


def mask_sensitive(text: str) -> str:
    """对日志中的敏感信息进行脱敏"""
    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ============== 异常安全处理 ==============


def classify_error(error: Exception) -> str:
    """将异常归类，便于日志聚合和告警分流。"""
    type_name = type(error).__name__
    if isinstance(error, HTTPException):
        if error.status_code == 429:
            return "rate_limited"
        if 400 <= error.status_code < 500:
            return "client_error"
        return "server_error"
    if type_name in {"AuthenticationError", "PermissionDeniedError"}:
        return "auth_error"
    if type_name in {"TimeoutError", "APITimeoutError"}:
        return "timeout"
    if type_name in {"ConnectionError", "APIConnectionError"}:
        return "upstream_connection"
    if type_name in {"RateLimitError"}:
        return "upstream_rate_limited"
    return "unknown"


def safe_error_message(error: Exception) -> str:
    """返回不泄露内部信息的错误消息"""
    error_map = {
        "ConnectionError": "AI 服务连接失败，请稍后重试",
        "APIConnectionError": "AI 服务连接失败，请稍后重试",
        "TimeoutError": "请求超时，请稍后重试",
        "APITimeoutError": "请求超时，请稍后重试",
        "AuthenticationError": "AI 服务认证失败，请联系管理员",
        "PermissionDeniedError": "AI 服务认证失败，请联系管理员",
        "RateLimitError": "AI 服务繁忙，请稍后重试",
    }
    type_name = type(error).__name__
    return error_map.get(type_name, "服务暂时不可用，请稍后重试")


# ============== 请求日志中间件 ==============


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件 — 请求日志 + 安全头"""

    _SENSITIVE_PATHS = {"/health", "/"}

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
        safe_query = mask_sensitive(str(request.url.query))

        logger.info(
            "request %s %s query=%s from %s ua=%s",
            request.method,
            request.url.path,
            safe_query or "-",
            client_ip,
            mask_sensitive(request.headers.get("User-Agent", "")),
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "unhandled error category=%s method=%s path=%s query=%s",
                classify_error(exc),
                request.method,
                request.url.path,
                safe_query or "-",
            )
            raise

        # 安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
