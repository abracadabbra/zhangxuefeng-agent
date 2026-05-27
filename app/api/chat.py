"""对话 API 路由 — 集成会话管理、SSE 流式输出、灵魂追问引擎"""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.schemas import ChatResponse, SessionInfo
from app.models.user_profile import UserProfile
from app.services.context import build_context_messages, extract_entities, merge_entities, ExtractedEntities
from app.services.llm import chat_completion
from app.services.session import (
    create_session,
    get_session,
    delete_session,
    add_message,
    get_history,
    update_context,
    SessionData,
)
from app.services.skill import load_skill
from app.services.soul_query import SoulQueryEngine, QueryState
from app.services.streaming import stream_chat_completion, format_sse_event

router = APIRouter(prefix="/api/v1", tags=["chat"])

# 灵魂追问引擎
soul_engine = SoulQueryEngine()

# 会话内的追问状态（内存缓存，会话过期后重置）
_query_states: dict[str, QueryState] = {}


def _get_query_state(session_id: str) -> QueryState:
    """获取或创建追问状态"""
    if session_id not in _query_states:
        _query_states[session_id] = QueryState()
    return _query_states[session_id]


# ============== 请求模型 ==============

class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(None, description="会话ID，空则创建新会话")
    message: str = Field(..., description="用户消息")
    user_context: Optional[dict] = Field(default=None, description="用户背景信息")
    stream: bool = Field(default=False, description="是否使用 SSE 流式输出")


class FeedbackRequest(BaseModel):
    """反馈请求"""
    session_id: str = Field(..., description="会话ID")
    message_index: int = Field(..., description="消息索引（从 0 开始）")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, description="评论")


# ============== API 端点 ==============

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """核心对话接口 — 支持流式和非流式"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 获取或创建会话
    session_id = req.session_id or str(uuid.uuid4())
    session = await get_session(session_id)
    if session is None:
        session = await create_session(session_id)

    # 更新用户上下文
    if req.user_context:
        await update_context(session_id, req.user_context)
        session.user_context.update(req.user_context)

    # 从消息中提取实体
    entities = extract_entities(req.message)
    extracted_dict = {}
    if entities.score:
        extracted_dict["分数"] = entities.score
    if entities.province:
        extracted_dict["省份"] = entities.province
    if entities.subject:
        extracted_dict["科类"] = entities.subject
    if entities.family_background:
        extracted_dict["家庭条件"] = entities.family_background
    if extracted_dict:
        await update_context(session_id, extracted_dict)
        session.user_context.update(extracted_dict)

    # 构建画像
    profile = UserProfile(**{
        "score": session.user_context.get("分数"),
        "province": session.user_context.get("省份"),
        "subject": session.user_context.get("科类"),
        "family_background": session.user_context.get("家庭条件"),
        "target_city": session.user_context.get("目标城市"),
        "risk_tolerance": session.user_context.get("风险偏好"),
        "career_goal": session.user_context.get("职业方向"),
    })

    # 灵魂追问
    query_state = _get_query_state(session_id)
    if not soul_engine.is_query_complete(profile):
        question = soul_engine.get_next_question(profile, query_state)
        if question:
            await add_message(session_id, "user", req.message)
            await add_message(session_id, "assistant", question)
            return ChatResponse(
                session_id=session_id,
                reply=question,
                model="soul-query-engine",
            )

    # 画像完整，调用 LLM
    skill_content = load_skill()
    history = await get_history(session_id, limit=20)
    messages = build_context_messages(
        skill_content, history, req.message, session.user_context
    )

    # 流式输出
    if req.stream:
        return StreamingResponse(
            _stream_generator(session_id, req.message, messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 非流式输出
    try:
        data = await chat_completion(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用异常: {e}")

    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage")

    # 保存消息
    await add_message(session_id, "user", req.message)
    await add_message(session_id, "assistant", reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        model=data.get("model", ""),
        usage=usage,
    )


async def _stream_generator(
    session_id: str,
    user_message: str,
    messages: list[dict],
):
    """SSE 流式响应生成器"""
    full_reply = ""

    try:
        async for event in stream_chat_completion(messages):
            if event["type"] == "text":
                full_reply += event["content"]
                yield format_sse_event(event)
            elif event["type"] == "tool_call":
                yield format_sse_event(event)
            elif event["type"] == "done":
                yield format_sse_event(event)
    except Exception as e:
        yield format_sse_event({"type": "error", "content": str(e)})

    # 保存完整回复
    await add_message(session_id, "user", user_message)
    await add_message(session_id, "assistant", full_reply)


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """获取会话信息"""
    session = await get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    return SessionInfo(
        session_id=session.session_id,
        created_at=session.created_at,
        message_count=len(session.messages),
        user_context=session.user_context,
    )


@router.delete("/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    """删除会话"""
    deleted = await delete_session(session_id)
    # 清理追问状态
    _query_states.pop(session_id, None)
    return {"status": "deleted" if deleted else "not_found", "session_id": session_id}


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """提交反馈"""
    session = await get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    if req.message_index < 0 or req.message_index >= len(session.messages):
        raise HTTPException(status_code=400, detail="消息索引无效")

    # 存储反馈到会话元数据
    if "feedback" not in session.metadata:
        session.metadata["feedback"] = []

    session.metadata["feedback"].append({
        "message_index": req.message_index,
        "rating": req.rating,
        "comment": req.comment,
        "timestamp": datetime.now().isoformat(),
    })

    from app.services.session import save_session
    await save_session(session)

    return {"status": "ok", "session_id": req.session_id}
