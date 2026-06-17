"""
系统端点：/、/health、/db/status、/tools、/cache/flush、反馈 API
"""

import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.dependencies import MODEL
from backend.security import validate_session_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== System Endpoints ==============


@router.get("/")
async def root():
    return {
        "status": "ok",
        "agent": "张雪峰 AI",
        "model": MODEL,
        "features": ["function_calling", "sse_streaming", "soul_query", "data_query"],
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.get("/db/status")
async def db_status():
    """数据库状态检查"""
    from contextlib import closing

    from backend.database import SessionLocal
    from backend.models import AdmissionScore, EnrollmentPlan, Major, School

    with closing(SessionLocal()) as db:
        try:
            return {
                "status": "connected",
                "tables": {
                    "schools": db.query(School).count(),
                    "majors": db.query(Major).count(),
                    "admission_scores": db.query(AdmissionScore).count(),
                    "enrollment_plans": db.query(EnrollmentPlan).count(),
                },
            }
        except Exception as e:
            logger.error(f"数据库状态检查失败: {e}")
            return {"status": "error", "detail": "数据库连接异常"}


@router.post("/cache/flush")
async def flush_cache():
    """清除所有应用缓存"""
    from backend.cache import cache_flush

    await cache_flush()
    return {"status": "ok", "message": "缓存已清除"}


@router.get("/tools")
async def list_tools():
    """返回所有已注册工具的定义"""
    from backend.tools.definitions import TOOLS

    return {"tools": TOOLS}


# ============== Feedback API ==============


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


@router.post("/api/v1/feedback")
async def submit_feedback(req: FeedbackRequest):
    """提交用户反馈"""
    validate_session_id(req.session_id)
    from backend.database import SessionLocal
    from backend.models.feedback import Feedback

    db = SessionLocal()
    try:
        fb = Feedback(
            session_id=req.session_id,
            message_index=req.message_index,
            rating=req.rating,
            comment=req.comment,
        )
        db.add(fb)
        db.commit()
        return {"status": "ok", "id": fb.id}
    finally:
        db.close()


@router.get("/api/v1/feedback/stats")
async def feedback_stats():
    """反馈统计"""
    from sqlalchemy import func

    from backend.database import SessionLocal
    from backend.models.feedback import Feedback

    db = SessionLocal()
    try:
        total = db.query(func.count(Feedback.id)).scalar()
        avg_rating = db.query(func.avg(Feedback.rating)).scalar()
        distribution = (
            db.query(Feedback.rating, func.count(Feedback.id)).group_by(Feedback.rating).all()
        )
        return {
            "total": total,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else 0,
            "distribution": {str(r): c for r, c in distribution},
        }
    finally:
        db.close()
