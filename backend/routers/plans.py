"""
招生计划查询 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.crud.enrollment_plan import get_enrollment_plans, get_plans_by_school, get_plans_by_major
from backend.schemas.enrollment_plan import EnrollmentPlanOut, EnrollmentPlanQuery

router = APIRouter(prefix="/plans", tags=["招生计划"])


@router.post("/search", summary="多条件查询招生计划")
def search_plans(query: EnrollmentPlanQuery, db: Session = Depends(get_db)):
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
    province: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    items = get_plans_by_school(db, school_id, province, year)
    return {"school_id": school_id, "count": len(items), "items": items}


@router.get("/major/{major_id}", summary="查询某专业招生计划（跨院校）")
def plans_by_major(
    major_id: int,
    province: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    items = get_plans_by_major(db, major_id, province, year)
    return {"major_id": major_id, "count": len(items), "items": items}
