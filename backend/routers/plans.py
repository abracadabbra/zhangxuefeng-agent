"""
招生计划查询 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.crud.enrollment_plan import (
    get_enrollment_plans,
    get_plans_by_major,
    get_plans_by_school,
)
from backend.database import get_db
from backend.schemas.enrollment_plan import EnrollmentPlanQuery

router = APIRouter(prefix="/plans", tags=["招生计划"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/search", summary="多条件查询招生计划")
def search_plans(query: EnrollmentPlanQuery, db: DbSession):
    items, total = get_enrollment_plans(db, query)
    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": items,
    }


@router.get("/school/{school_id}", summary="查询某院校招生计划")
def plans_by_school(
    school_id: int,
    db: DbSession,
    province: str | None = None,
    year: int | None = None,
):
    items = get_plans_by_school(db, school_id, province, year)
    return {"school_id": school_id, "count": len(items), "items": items}


@router.get("/major/{major_id}", summary="查询某专业招生计划（跨院校）")
def plans_by_major(
    major_id: int,
    db: DbSession,
    province: str | None = None,
    year: int | None = None,
):
    items = get_plans_by_major(db, major_id, province, year)
    return {"major_id": major_id, "count": len(items), "items": items}
