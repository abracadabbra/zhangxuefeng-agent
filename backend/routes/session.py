"""
会话相关端点：/sessions、/session/*
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from backend.dependencies import session_store
from backend.security import validate_session_id

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    user_context: dict | None
    messages: list[dict] = Field(default_factory=list, description="完整消息历史")


class RecommendationFavorites(BaseModel):
    favorite_keys: list[str] = Field(default_factory=list, description="收藏的推荐 key 列表")


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    """列出最近的会话"""
    return session_store.list_recent(limit=limit)


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    validate_session_id(session_id)
    s = session_store.get_or_create(session_id)
    return SessionInfo(
        session_id=session_id,
        created_at=s["created_at"],
        message_count=s["message_count"],
        user_context=s["user_context"],
        messages=s["history"],
    )


@router.get("/session/{session_id}/favorites", response_model=RecommendationFavorites)
async def get_recommendation_favorites(session_id: str):
    """读取当前会话收藏的推荐项。"""
    validate_session_id(session_id)
    return RecommendationFavorites(
        favorite_keys=session_store.get_recommendation_favorites(session_id)
    )


@router.put("/session/{session_id}/favorites", response_model=RecommendationFavorites)
async def update_recommendation_favorites(
    session_id: str,
    payload: RecommendationFavorites,
):
    """覆盖保存当前会话收藏的推荐项。"""
    validate_session_id(session_id)
    session_store.save_recommendation_favorites(session_id, payload.favorite_keys)
    return RecommendationFavorites(
        favorite_keys=session_store.get_recommendation_favorites(session_id)
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    validate_session_id(session_id)
    session_store.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/session/{session_id}/export")
async def export_session(session_id: str):
    """导出志愿建议报告为 Markdown"""
    validate_session_id(session_id)
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    s = session_store.get_or_create(session_id)
    session_data = {
        "session_id": session_id,
        "created_at": s["created_at"],
        "message_count": s["message_count"],
        "user_context": s.get("user_context", {}),
        "history": s["history"],
        "recommendations": s.get("recommendations", []),
        "summary": s.get("summary", ""),
        "gradient_summary": s.get("gradient_summary", {}),
        "favorite_keys": session_store.get_recommendation_favorites(session_id),
    }

    from backend.export import generate_chat_markdown

    return PlainTextResponse(
        content=generate_chat_markdown(session_data),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=chat-{session_id[:8]}.md"},
    )


@router.get("/session/{session_id}/export/pdf")
async def export_session_pdf(session_id: str):
    """导出对话记录为 PDF（报纸风格排版）"""
    validate_session_id(session_id)
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    s = session_store.get_or_create(session_id)
    session_data = {
        "session_id": session_id,
        "created_at": s["created_at"],
        "message_count": s["message_count"],
        "user_context": s.get("user_context", {}),
        "history": s["history"],
        "recommendations": s.get("recommendations", []),
        "summary": s.get("summary", ""),
        "gradient_summary": s.get("gradient_summary", {}),
        "favorite_keys": session_store.get_recommendation_favorites(session_id),
    }

    from backend.export import generate_chat_pdf

    try:
        pdf_bytes = generate_chat_pdf(session_data)
    except Exception as e:
        logger.error(f"PDF 导出失败: {e}")
        from backend.security import safe_error_message

        raise HTTPException(status_code=500, detail=safe_error_message(e)) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="chat-{session_id[:8]}.pdf"',
        },
    )
