"""
对话相关端点：/chat、/recommend、SSE 流式生成器
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.agent.core import AgentCore
from backend.dependencies import (
    MODEL,
    OPENAI_API_KEY,
    USE_LANGCHAIN,
    get_agent,
    session_store,
    soul_engine,
)
from backend.security import (
    safe_error_message,
    validate_message,
    validate_session_id,
    validate_user_context,
)
from backend.soul_query import QueryState
from backend.user_profile import (
    UserProfile,
    load_profile,
    save_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ============== Pydantic Models ==============


class ChatRequest(BaseModel):
    session_id: str | None = Field(None, description="会话ID，空则创建新会话")
    message: str = Field(..., description="用户消息")
    user_context: dict | None = Field(default=None, description="用户背景信息")
    stream: bool = Field(default=False, description="是否使用 SSE 流式输出")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str
    tool_calls: list[dict] = Field(default_factory=list, description="工具调用记录")
    usage: dict | None = None


class RecommendRequest(BaseModel):
    session_id: str | None = Field(None, description="会话ID")
    message: str = Field(..., description="推荐请求，如'推荐计算机专业'")
    user_context: dict | None = Field(default=None, description="用户背景信息")


# ============== Helpers ==============

# 中文字段名 -> UserProfile 字段名映射
_CONTEXT_KEY_MAP = {
    "分数": "score",
    "省份": "province",
    "科类": "subject",
    "家庭条件": "family_background",
    "目标城市": "target_city",
    "风险偏好": "risk_tolerance",
    "职业方向": "career_goal",
}


def _extract_profile_from_message(message: str, profile: UserProfile) -> bool:
    """从用户消息中提取画像信息（简单关键词匹配），返回 True 表示画像有更新"""
    import re

    updated = False

    score_match = re.search(r"(\d{2,3})\s*分", message)
    if score_match and profile.score is None:
        score = int(score_match.group(1))
        if 100 <= score <= 750:
            profile.score = score
            updated = True

    provinces = [
        "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
        "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
        "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西",
        "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    ]
    for p in provinces:
        if p in message and profile.province is None:
            profile.province = p
            updated = True
            break

    if profile.subject is None:
        if "文科" in message or "文" == message.strip():
            profile.subject = "文科"
            updated = True
        elif "理科" in message or "理" == message.strip():
            profile.subject = "理科"
            updated = True

    if profile.family_background is None:
        if "工薪" in message or "打工" in message or "普通家庭" in message:
            profile.family_background = "工薪阶层"
            updated = True
        elif "做生意" in message or "经商" in message or "企业" in message:
            profile.family_background = "经商家庭"
            updated = True
        elif "体制内" in message or "公务员" in message or "事业单位" in message:
            profile.family_background = "体制内家庭"
            updated = True

    return updated


# ============== SSE Stream Generators ==============


async def _stream_response(
    agent_instance: AgentCore,
    messages: list[dict],
    session_id: str,
    user_message: str,
    user_context: dict,
):
    """SSE 流式响应生成器（AgentCore 模式）"""
    full_reply = ""
    tool_calls_log = []

    try:
        async for event in agent_instance.chat_stream(messages, user_context=user_context):
            if event["type"] == "text":
                full_reply += event["content"]
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "text", "content": event["content"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_call":
                tool_calls_log.append({"name": event["name"], "arguments": event["arguments"]})
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "tool_call", "name": event["name"], "arguments": event["arguments"]},
                        ensure_ascii=False,
                    ),
                }
            elif event["type"] == "tool_result":
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "tool_result", "name": event["name"], "result": event["result"]},
                        ensure_ascii=False,
                    ),
                }
            elif event["type"] == "done":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "done", "usage": event["usage"]}, ensure_ascii=False),
                }
    except Exception as e:
        logger.error(f"LLM 流式调用失败: {type(e).__name__}: {e}", exc_info=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "text", "content": f"\n\n{safe_error_message(e)}"}, ensure_ascii=False),
        }
        yield {
            "event": "message",
            "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
        }

    session_store.add_message(session_id, "user", user_message)
    session_store.add_message(session_id, "assistant", full_reply)


async def _stream_response_langchain(
    agent_instance,
    session_id: str,
    user_message: str,
    user_context: dict,
):
    """LangChain Agent 的 SSE 流式响应生成器"""
    try:
        async for event in agent_instance.chat_stream(
            message=user_message,
            session_id=session_id,
            user_context=user_context,
        ):
            if event["type"] == "text":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "text", "content": event["content"]}, ensure_ascii=False),
                }
            elif event["type"] == "tool_call":
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "tool_call", "name": event["name"], "arguments": event["arguments"]},
                        ensure_ascii=False,
                    ),
                }
            elif event["type"] == "tool_result":
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "tool_result", "name": event["name"], "result": event["result"]},
                        ensure_ascii=False,
                    ),
                }
            elif event["type"] == "done":
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
                }
    except Exception as e:
        logger.error(f"LangChain 流式调用失败: {type(e).__name__}: {e}", exc_info=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "text", "content": f"\n\n{safe_error_message(e)}"}, ensure_ascii=False),
        }
        yield {
            "event": "message",
            "data": json.dumps({"type": "done", "usage": None}, ensure_ascii=False),
        }


# ============== Endpoints ==============


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """核心对话接口 -- 支持非流式和 SSE 流式输出"""
    safe_message = validate_message(req.message)
    session_id = validate_session_id(req.session_id)
    safe_context = validate_user_context(req.user_context)

    # 获取或创建会话
    session = session_store.get_or_create(session_id, user_context=safe_context)
    query_state: QueryState = session["query_state"]

    # 加载用户画像
    try:
        profile = await load_profile(session_id)
    except Exception:
        profile = UserProfile()

    # 合并 user_context 到 profile（供灵魂追问使用）
    if session["user_context"]:
        for key, val in session["user_context"].items():
            if val is None:
                continue
            field = _CONTEXT_KEY_MAP.get(key)
            if field and field in UserProfile.model_fields and getattr(profile, field, None) is None:
                setattr(profile, field, val)

    profile_updated = _extract_profile_from_message(safe_message, profile)
    if profile_updated:
        try:
            await save_profile(session_id, profile)
        except Exception:
            pass

    if profile.is_required_complete():
        try:
            await save_profile(session_id, profile)
        except Exception:
            pass

    # 灵魂追问
    if not soul_engine.is_query_complete(profile):
        question = soul_engine.get_next_question(profile, query_state)
        if question:
            session_store.add_message(session_id, "user", safe_message)
            session_store.add_message(session_id, "assistant", question)
            session_store.update_query_state(session_id, query_state)
            return ChatResponse(
                session_id=session_id,
                reply=question,
                model="soul-query-engine",
                usage=None,
            )

    # 画像完整，正常调用 LLM
    session["user_context"] = profile.to_context_dict()
    session_store.update_context(session_id, session["user_context"])

    if not OPENAI_API_KEY and not USE_LANGCHAIN:
        error_reply = "抱歉，AI 服务暂时不可用（API Key 未配置）。请联系管理员配置 OPENAI_API_KEY 环境变量。"
        session_store.add_message(session_id, "user", safe_message)
        session_store.add_message(session_id, "assistant", error_reply)
        return ChatResponse(
            session_id=session_id,
            reply=error_reply,
            model=MODEL,
            tool_calls=[],
            usage=None,
        )

    agent_instance = get_agent()

    # LangChain Agent 模式
    if USE_LANGCHAIN:
        if req.stream:
            return EventSourceResponse(
                _stream_response_langchain(agent_instance, session_id, safe_message, session["user_context"]),
                media_type="text/event-stream",
            )
        result = await agent_instance.chat(
            message=safe_message,
            session_id=session_id,
            user_context=session["user_context"],
        )
        return ChatResponse(
            session_id=session_id,
            reply=result["reply"],
            model="langchain-agent",
            tool_calls=result.get("tool_calls", []),
            usage=None,
        )

    # AgentCore 模式
    messages = list(session["history"])
    messages.append({"role": "user", "content": safe_message})

    if req.stream:
        return EventSourceResponse(
            _stream_response(agent_instance, messages, session_id, safe_message, session["user_context"]),
            media_type="text/event-stream",
        )

    try:
        result = await agent_instance.chat(messages, user_context=session["user_context"])
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        error_reply = safe_error_message(e)
        session_store.add_message(session_id, "user", safe_message)
        session_store.add_message(session_id, "assistant", error_reply)
        return ChatResponse(
            session_id=session_id,
            reply=error_reply,
            model=MODEL,
            tool_calls=[],
            usage=None,
        )

    session_store.add_message(session_id, "user", safe_message)
    session_store.add_message(session_id, "assistant", result["reply"])

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        model=MODEL,
        tool_calls=result["tool_calls"],
        usage=result["usage"],
    )


@router.post("/recommend")
async def recommend(req: RecommendRequest):
    """结构化推荐接口 -- 返回学校/专业推荐结果"""
    if not USE_LANGCHAIN:
        raise HTTPException(status_code=501, detail="推荐接口需要启用 LangChain (USE_LANGCHAIN=true)")

    safe_message = validate_message(req.message)
    session_id = validate_session_id(req.session_id)
    safe_context = validate_user_context(req.user_context)
    agent_instance = get_agent()

    if not hasattr(agent_instance, "chat_structured"):
        raise HTTPException(status_code=501, detail="Agent 不支持结构化输出")

    try:
        result = await agent_instance.chat_structured(
            message=safe_message,
            session_id=session_id,
            user_context=safe_context,
        )
        return {
            "session_id": session_id,
            "recommendations": result.recommendations,
            "summary": result.summary,
        }
    except Exception as e:
        logger.error(f"推荐失败: {e}")
        raise HTTPException(status_code=500, detail=safe_error_message(e))
