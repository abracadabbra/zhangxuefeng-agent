"""
专业查询 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.crud.major import get_major, get_majors, get_major_by_name, get_hot_majors
from backend.schemas.major import MajorOut, MajorQuery

router = APIRouter(prefix="/majors", tags=["专业"])


@router.get("/{major_id}", response_model=MajorOut, summary="根据ID查询专业")
def read_major(major_id: int, db: Session = Depends(get_db)):
    major = get_major(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    return major


@router.get("/by-name/{name}", response_model=MajorOut, summary="根据名称查询专业")
def read_major_by_name(name: str, db: Session = Depends(get_db)):
    major = get_major_by_name(db, name)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    return major


@router.get("/hot/list", summary="获取热门专业")
def list_hot_majors(limit: int = 20, db: Session = Depends(get_db)):
    items = get_hot_majors(db, limit)
    return {"items": [MajorOut.model_validate(m) for m in items]}


@router.post("/search", summary="多条件查询专业列表")
def search_majors(query: MajorQuery, db: Session = Depends(get_db)):
    items, total = get_majors(db, query)
    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": [MajorOut.model_validate(m) for m in items],
    }
