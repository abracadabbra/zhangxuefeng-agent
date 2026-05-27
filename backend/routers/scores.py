"""
录取分数线查询 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.crud.admission_score import (
    get_admission_scores, get_scores_by_school, get_scores_by_major, get_score_stats
)
from backend.schemas.admission_score import AdmissionScoreOut, AdmissionScoreQuery, ScoreStats

router = APIRouter(prefix="/scores", tags=["分数线"])


@router.post("/search", summary="多条件查询分数线")
def search_scores(query: AdmissionScoreQuery, db: Session = Depends(get_db)):
    """支持按学校名/专业名/省份/年份/分数范围等组合查询"""
    items, total = get_admission_scores(db, query)
    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": items,
    }


@router.get("/school/{school_id}", summary="查询某院校分数线")
def scores_by_school(
    school_id: int,
    province: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    items = get_scores_by_school(db, school_id, province, year)
    return {"school_id": school_id, "count": len(items), "items": items}


@router.get("/major/{major_id}", summary="查询某专业分数线（跨院校）")
def scores_by_major(
    major_id: int,
    province: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    items = get_scores_by_major(db, major_id, province, year)
    return {"major_id": major_id, "count": len(items), "items": items}


@router.get("/stats", summary="获取分数统计信息", response_model=ScoreStats)
def score_stats(
    school_id: int,
    province: str,
    year: int,
    major_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    stats = get_score_stats(db, school_id, major_id, province, year)
    if not stats:
        return {"message": "未找到数据"}
    return stats
