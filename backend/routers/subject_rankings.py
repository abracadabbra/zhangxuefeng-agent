"""
学科排名查询 API 路由
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.crud.subject_ranking import get_subject_rankings
from backend.database import get_db
from backend.schemas.subject_ranking import SubjectRankingQuery

router = APIRouter(prefix="/subject-rankings", tags=["学科排名"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/search", summary="多条件查询学科排名")
def search_subject_rankings(query: SubjectRankingQuery, db: DbSession):
    items, total = get_subject_rankings(db, query)
    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "items": items,
    }
