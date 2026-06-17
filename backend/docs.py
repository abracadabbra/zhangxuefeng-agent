"""
API 文档自动生成模块

通过 FastAPI 原生 OpenAPI 支持增强文档：
- 接口分组标签描述
- 请求/响应示例
- 错误码说明
- 自定义 OpenAPI schema
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# ============== 标签元数据 ==============

TAGS_METADATA = [
    {
        "name": "对话",
        "description": (
            "核心对话接口。支持普通请求和 SSE 流式输出两种模式。\n\n"
            "**流程**: 用户发送消息 -> 灵魂追问引擎检查画像完整性 -> "
            "画像未完整时返回追问问题 -> 画像完整后调用 LLM 生成回复。\n\n"
            "支持 Function Calling，可自动调用搜索院校、专业、录取分数等工具。"
        ),
    },
    {
        "name": "用户画像",
        "description": (
            "管理用户画像信息（分数、省份、科类、家庭条件等）。\n\n"
            "画像信息用于灵魂追问引擎判断是否可以进入正式咨询，"
            "也作为上下文注入 LLM 以提供个性化建议。"
        ),
    },
    {
        "name": "会话管理",
        "description": (
            "会话的创建、查询、删除和导出。\n\n"
            "每个会话维护独立的对话历史和用户上下文。"
            "支持导出为 Markdown 和 PDF 格式。"
        ),
    },
    {
        "name": "系统",
        "description": (
            "系统健康检查、数据库状态、工具列表、缓存管理和用户反馈。\n\n"
            "这些端点用于运维监控和系统管理。"
        ),
    },
    {
        "name": "院校查询",
        "description": "查询院校信息，包括基本信息、排名、录取分数等。",
    },
    {
        "name": "专业查询",
        "description": "查询专业信息，包括就业前景、薪资水平、开设院校等。",
    },
    {
        "name": "录取分数",
        "description": "查询各院校各专业的历年录取分数线。",
    },
    {
        "name": "招生计划",
        "description": "查询各院校各专业的招生计划。",
    },
    {
        "name": "学科排名",
        "description": "查询学科评估排名信息。",
    },
]

# ============== 错误码说明 ==============

ERROR_CODES = {
    400: {
        "description": "请求参数错误",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_message": {
                        "summary": "消息校验失败",
                        "value": {"detail": "消息内容不能为空"},
                    },
                    "invalid_session": {
                        "summary": "会话ID格式错误",
                        "value": {"detail": "无效的会话ID格式"},
                    },
                }
            }
        },
    },
    404: {
        "description": "资源不存在",
        "content": {
            "application/json": {
                "examples": {
                    "session_not_found": {
                        "summary": "会话不存在",
                        "value": {"detail": "会话不存在"},
                    },
                }
            }
        },
    },
    422: {
        "description": "请求体校验失败",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "type": "missing",
                            "loc": ["body", "message"],
                            "msg": "Field required",
                            "input": {},
                        }
                    ]
                }
            }
        },
    },
    429: {
        "description": "请求频率超限",
        "content": {"application/json": {"example": {"detail": "请求过于频繁，请稍后再试"}}},
    },
    500: {
        "description": "服务器内部错误",
        "content": {
            "application/json": {
                "examples": {
                    "llm_error": {
                        "summary": "LLM 调用失败",
                        "value": {"detail": "AI 服务暂时不可用，请稍后重试"},
                    },
                    "db_error": {
                        "summary": "数据库异常",
                        "value": {"detail": "数据库连接异常"},
                    },
                }
            }
        },
    },
    501: {
        "description": "功能未启用",
        "content": {
            "application/json": {
                "example": {"detail": "推荐接口需要启用 LangChain (USE_LANGCHAIN=true)"}
            }
        },
    },
}

# ============== 请求/响应示例 ==============

CHAT_EXAMPLES = {
    "basic_chat": {
        "summary": "基础对话",
        "description": "发送一条消息进行咨询",
        "value": {
            "message": "我考了580分，河北理科，能上什么学校？",
            "stream": False,
        },
    },
    "chat_with_context": {
        "summary": "带画像的对话",
        "description": "携带用户背景信息进行咨询",
        "value": {
            "message": "推荐几个计算机专业的学校",
            "user_context": {
                "分数": 620,
                "省份": "山东",
                "科类": "理科",
                "家庭条件": "工薪阶层",
            },
            "stream": False,
        },
    },
    "streaming_chat": {
        "summary": "流式对话",
        "description": "使用 SSE 流式输出获取回复",
        "value": {
            "message": "计算机和电子信息专业哪个好？",
            "stream": True,
        },
    },
}

PROFILE_EXAMPLES = {
    "update_score": {
        "summary": "更新分数",
        "value": {"field": "score", "value": "620"},
    },
    "update_province": {
        "summary": "更新省份",
        "value": {"field": "province", "value": "山东"},
    },
    "update_subject": {
        "summary": "更新科类",
        "value": {"field": "subject", "value": "理科"},
    },
}

FEEDBACK_EXAMPLES = {
    "positive": {
        "summary": "好评反馈",
        "value": {
            "session_id": "abc123",
            "message_index": 2,
            "rating": 5,
            "comment": "回答非常详细，很有帮助",
        },
    },
    "negative": {
        "summary": "差评反馈",
        "value": {
            "session_id": "abc123",
            "message_index": 5,
            "rating": 2,
            "comment": "推荐的学校不太合适",
        },
    },
}


# ============== OpenAPI Schema 生成 ==============


def custom_openapi(app: FastAPI) -> dict:
    """生成自定义 OpenAPI schema，包含增强的文档信息。"""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAGS_METADATA,
    )

    # 补充 info 信息
    schema["info"]["contact"] = {
        "name": "张雪峰 AI 团队",
        "url": "https://github.com/zhangxuefeng-agent",
    }
    schema["info"]["license"] = {
        "name": "MIT",
    }

    # 全局错误码说明追加到 description
    error_doc = "\n\n---\n\n## 通用错误码\n\n"
    error_doc += "| 状态码 | 说明 |\n|--------|------|\n"
    for code, info in ERROR_CODES.items():
        error_doc += f"| `{code}` | {info['description']} |\n"
    schema["info"]["description"] = (schema["info"].get("description", "") or "") + error_doc

    # 为 paths 补充通用 responses
    for _path, methods in schema.get("paths", {}).items():
        for _method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            # 补充 429 和 500（如果未声明）
            if "429" not in responses:
                responses["429"] = ERROR_CODES[429]
            if "500" not in responses:
                responses["500"] = ERROR_CODES[500]

    app.openapi_schema = schema
    return schema


def setup_docs(app: FastAPI) -> None:
    """配置 API 文档端点和自定义 schema。"""
    app.openapi_tags = TAGS_METADATA
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]
