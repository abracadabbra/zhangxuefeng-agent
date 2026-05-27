"""
反馈 API 路由

端点：
- POST /api/v1/feedback — 提交反馈
- GET /api/v1/feedback/stats — 获取反馈统计
- GET /api/v1/feedback/session/{session_id} — 获取会话反馈
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.feedback import (
    FeedbackItem,
    FeedbackStats,
    save_feedback,
    get_session_feedbacks,
    get_feedback_stats,
)
from app.services.session import get_session

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


# ============== 请求模型 ==============

class FeedbackRequest(BaseModel):
    """反馈提交请求"""
    session_id: str = Field(..., description="会话ID")
    message_index: int = Field(..., description="消息索引")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, description="评论")


class FeedbackResponse(BaseModel):
    """反馈提交响应"""
    feedback_id: str
    session_id: str
    category: str
    status: str = "ok"


# ============== API 端点 ==============

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """提交反馈"""
    # 验证会话存在
    session = await get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 验证消息索引
    if req.message_index < 0 or req.message_index >= len(session.messages):
        raise HTTPException(status_code=400, detail="消息索引无效")

    # 创建反馈
    feedback = FeedbackItem(
        feedback_id=str(uuid.uuid4()),
        session_id=req.session_id,
        message_index=req.message_index,
        rating=req.rating,
        comment=req.comment,
    )

    await save_feedback(feedback)

    return FeedbackResponse(
        feedback_id=feedback.feedback_id,
        session_id=req.session_id,
        category=feedback.category or "其他",
    )


@router.get("/stats", response_model=FeedbackStats)
async def get_stats():
    """获取反馈统计"""
    return await get_feedback_stats()


@router.get("/session/{session_id}")
async def get_session_feedback(session_id: str):
    """获取会话的所有反馈"""
    feedbacks = await get_session_feedbacks(session_id)
    return {
        "session_id": session_id,
        "count": len(feedbacks),
        "feedbacks": [fb.model_dump() for fb in feedbacks],
    }
