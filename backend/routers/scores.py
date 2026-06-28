"""
录取分数线查询 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.cache import cache_get, cache_set
from backend.crud.admission_score import (
    get_admission_scores,
    get_score_stats,
    get_scores_by_major,
    get_scores_by_school,
)
from backend.database import get_db
from backend.schemas.admission_score import AdmissionScoreQuery, ScoreStats

router = APIRouter(prefix="/scores", tags=["分数线"])
DbSession = Annotated[Session, Depends(get_db)]


def _serialize_score(r) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "major_id": r.major_id,
        "major_label": r.major_label,
        "province": r.province,
        "year": r.year,
        "batch": r.batch,
        "subject_type": r.subject_type,
        "min_score": r.min_score,
        "avg_score": r.avg_score,
        "max_score": r.max_score,
        "min_rank": r.min_rank,
        "plan_count": r.plan_count,
    }


@router.post("/search", summary="多条件查询分数线")
async def search_scores(query: AdmissionScoreQuery, db: DbSession):
    """支持按学校名/投档单位/省份/年份/分数范围等组合查询"""
    params = query.model_dump()
    cached = await cache_get("score_search", **params)
    if cached:
        return cached
    items, total = get_admission_scores(db, query)
    result = {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": items,
    }
    await cache_set("score_search", result, **params)
    return result


@router.get("/school/{school_id}", summary="查询某院校分数线")
async def scores_by_school(
    school_id: int,
    db: DbSession,
    province: str | None = None,
    year: int | None = None,
):
    cached = await cache_get("score_school", school_id=school_id, province=province, year=year)
    if cached:
        return cached
    items = get_scores_by_school(db, school_id, province, year)
    result = {
        "school_id": school_id,
        "count": len(items),
        "items": [_serialize_score(r) for r in items],
    }
    await cache_set("score_school", result, school_id=school_id, province=province, year=year)
    return result


@router.get("/major/{major_id}", summary="查询某专业分数线（跨院校）")
async def scores_by_major(
    major_id: int,
    db: DbSession,
    province: str | None = None,
    year: int | None = None,
):
    cached = await cache_get("score_major", major_id=major_id, province=province, year=year)
    if cached:
        return cached
    items = get_scores_by_major(db, major_id, province, year)
    result = {
        "major_id": major_id,
        "count": len(items),
        "items": [_serialize_score(r) for r in items],
    }
    await cache_set("score_major", result, major_id=major_id, province=province, year=year)
    return result


@router.get("/stats", summary="获取分数统计信息", response_model=ScoreStats)
async def score_stats(
    school_id: int,
    province: str,
    year: int,
    db: DbSession,
    major_id: int | None = None,
):
    cached = await cache_get(
        "score_stats",
        school_id=school_id,
        province=province,
        year=year,
        major_id=major_id,
    )
    if cached:
        return cached
    stats = get_score_stats(db, school_id, major_id, province, year)
    if not stats:
        return {"message": "未找到数据"}
    result = stats.model_dump() if hasattr(stats, "model_dump") else stats
    await cache_set(
        "score_stats",
        result,
        school_id=school_id,
        province=province,
        year=year,
        major_id=major_id,
    )
    return result
