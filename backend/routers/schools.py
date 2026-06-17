"""
院校查询 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.cache import cache_get, cache_set
from backend.crud.school import get_school, get_school_by_name, get_schools
from backend.database import get_db
from backend.schemas.school import SchoolOut, SchoolQuery

router = APIRouter(prefix="/schools", tags=["院校"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{school_id}", response_model=SchoolOut, summary="根据ID查询院校")
async def read_school(school_id: int, db: DbSession):
    cached = await cache_get("school", id=school_id)
    if cached:
        return cached
    school = get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="院校不存在")
    result = SchoolOut.model_validate(school).model_dump()
    await cache_set("school", result, id=school_id)
    return result


@router.get("/by-name/{name}", response_model=SchoolOut, summary="根据名称查询院校")
async def read_school_by_name(name: str, db: DbSession):
    cached = await cache_get("school_name", name=name)
    if cached:
        return cached
    school = get_school_by_name(db, name)
    if not school:
        raise HTTPException(status_code=404, detail="院校不存在")
    result = SchoolOut.model_validate(school).model_dump()
    await cache_set("school_name", result, name=name)
    return result


@router.post("/search", summary="多条件查询院校列表")
async def search_schools(query: SchoolQuery, db: DbSession):
    params = query.model_dump()
    cached = await cache_get("school_search", **params)
    if cached:
        return cached
    items, total = get_schools(db, query)
    result = {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": [SchoolOut.model_validate(s).model_dump() for s in items],
    }
    await cache_set("school_search", result, **params)
    return result
