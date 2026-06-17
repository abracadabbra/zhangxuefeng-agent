import contextvars
import logging

from fastapi import HTTPException

from backend.agent.core import _format_tool_arguments_for_log
from backend.logging_config import request_filter
from backend.routes.chat import _summarize_tool_calls
from backend.security import classify_error, mask_sensitive, safe_error_message


def test_mask_sensitive_redacts_tokens_in_query_strings():
    text = "api_key=sk-1234567890abcdef&token=plain-token&province=北京"

    masked = mask_sensitive(text)

    assert "sk-1234567890abcdef" not in masked
    assert "plain-token" not in masked
    assert "api_key=****" in masked
    assert "token=****" in masked
    assert "province=北京" in masked


def test_mask_sensitive_redacts_bearer_tokens():
    text = (
        "Authorization: Bearer eyJhbGciOiJIUzI1Ni.fake.signature "
        "curl -H 'Authorization: Bearer plain-token-123'"
    )

    masked = mask_sensitive(text)

    assert "eyJhbGciOiJIUzI1Ni.fake.signature" not in masked
    assert "plain-token-123" not in masked
    assert "Authorization: Bearer ****" in masked
    assert "'Authorization: Bearer ****'" in masked


def test_mask_sensitive_redacts_contact_details():
    text = "phone=13812345678 email=student@example.com"

    masked = mask_sensitive(text)

    assert "13812345678" not in masked
    assert "student@example.com" not in masked
    assert "138****5678" in masked
    assert "****@example.com" in masked


def test_classify_error_groups_http_errors():
    assert classify_error(HTTPException(status_code=400, detail="bad")) == "client_error"
    assert classify_error(HTTPException(status_code=429, detail="slow down")) == "rate_limited"
    assert classify_error(HTTPException(status_code=503, detail="down")) == "server_error"


def test_classify_error_groups_upstream_errors():
    connection_error = type("APIConnectionError", (Exception,), {})
    rate_limit_error = type("RateLimitError", (Exception,), {})

    assert classify_error(connection_error()) == "upstream_connection"
    assert classify_error(TimeoutError()) == "timeout"
    assert classify_error(rate_limit_error()) == "upstream_rate_limited"
    assert classify_error(RuntimeError("boom")) == "unknown"


def test_safe_error_message_handles_common_upstream_errors():
    timeout_error = type("APITimeoutError", (Exception,), {})
    rate_limit_error = type("RateLimitError", (Exception,), {})

    assert safe_error_message(timeout_error()) == "请求超时，请稍后重试"
    assert safe_error_message(rate_limit_error()) == "AI 服务繁忙，请稍后重试"


def test_tool_call_summary_omits_sensitive_argument_values():
    summary = _summarize_tool_calls(
        [
            {
                "name": "search_schools",
                "arguments": {
                    "api_key": "sk-1234567890abcdef",
                    "province": "北京",
                    "phone": "13812345678",
                },
                "result": "结果内容",
            }
        ]
    )

    assert summary == [
        {
            "name": "search_schools",
            "argument_keys": ["api_key", "phone", "province"],
            "result_chars": 4,
        }
    ]
    assert "sk-1234567890abcdef" not in str(summary)
    assert "13812345678" not in str(summary)


def test_tool_argument_log_formatter_masks_sensitive_values():
    formatted = _format_tool_arguments_for_log(
        {
            "api_key": "sk-1234567890abcdef",
            "token": "plain-token",
            "phone": "13812345678",
            "email": "student@example.com",
            "province": "北京",
        }
    )

    assert "sk-1234567890abcdef" not in formatted
    assert "plain-token" not in formatted
    assert "13812345678" not in formatted
    assert "student@example.com" not in formatted
    assert "api_key=****" in formatted or '"api_key": "****"' in formatted
    assert "province" in formatted
    assert "北京" in formatted


def test_request_context_filter_isolates_copied_contexts():
    tokens = request_filter.set_context("outer-request", "outer-user")
    try:
        copied = contextvars.copy_context()
        copied.run(request_filter.set_context, "inner-request", "inner-user")

        record = logging.makeLogRecord({"msg": "test"})
        request_filter.filter(record)

        assert record.request_id == "outer-request"
        assert record.user_id == "outer-user"
    finally:
        request_filter.reset_context(tokens)
