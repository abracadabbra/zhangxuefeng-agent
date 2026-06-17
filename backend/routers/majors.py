"""
专业查询 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.cache import cache_get, cache_set
from backend.crud.major import get_hot_majors, get_major, get_major_by_name, get_majors
from backend.database import get_db
from backend.schemas.major import MajorOut, MajorQuery

router = APIRouter(prefix="/majors", tags=["专业"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{major_id}", response_model=MajorOut, summary="根据ID查询专业")
async def read_major(major_id: int, db: DbSession):
    cached = await cache_get("major", id=major_id)
    if cached:
        return cached
    major = get_major(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    result = MajorOut.model_validate(major).model_dump()
    await cache_set("major", result, id=major_id)
    return result


@router.get("/by-name/{name}", response_model=MajorOut, summary="根据名称查询专业")
async def read_major_by_name(name: str, db: DbSession):
    cached = await cache_get("major_name", name=name)
    if cached:
        return cached
    major = get_major_by_name(db, name)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    result = MajorOut.model_validate(major).model_dump()
    await cache_set("major_name", result, name=name)
    return result


@router.get("/hot/list", summary="获取热门专业")
async def list_hot_majors(db: DbSession, limit: int = 20):
    cached = await cache_get("major_hot", limit=limit)
    if cached:
        return cached
    items = get_hot_majors(db, limit)
    result = {"items": [MajorOut.model_validate(m).model_dump() for m in items]}
    await cache_set("major_hot", result, limit=limit)
    return result


@router.post("/search", summary="多条件查询专业列表")
async def search_majors(query: MajorQuery, db: DbSession):
    params = query.model_dump()
    cached = await cache_get("major_search", **params)
    if cached:
        return cached
    items, total = get_majors(db, query)
    result = {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": [MajorOut.model_validate(m).model_dump() for m in items],
    }
    await cache_set("major_search", result, **params)
    return result
