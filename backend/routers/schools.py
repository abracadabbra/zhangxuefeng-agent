"""
院校查询 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.crud.school import get_school, get_schools, get_school_by_name
from backend.schemas.school import SchoolOut, SchoolQuery

router = APIRouter(prefix="/schools", tags=["院校"])


@router.get("/{school_id}", response_model=SchoolOut, summary="根据ID查询院校")
def read_school(school_id: int, db: Session = Depends(get_db)):
    school = get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="院校不存在")
    return school


@router.get("/by-name/{name}", response_model=SchoolOut, summary="根据名称查询院校")
def read_school_by_name(name: str, db: Session = Depends(get_db)):
    school = get_school_by_name(db, name)
    if not school:
        raise HTTPException(status_code=404, detail="院校不存在")
    return school


@router.post("/search", summary="多条件查询院校列表")
def search_schools(query: SchoolQuery, db: Session = Depends(get_db)):
    items, total = get_schools(db, query)
    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": [SchoolOut.model_validate(s) for s in items],
    }
