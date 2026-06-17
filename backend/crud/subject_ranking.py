"""
学科排名 CRUD 操作
"""

from sqlalchemy.orm import Session

from backend.models.school import School
from backend.models.subject_ranking import SubjectRanking
from backend.schemas.subject_ranking import SubjectRankingQuery


def get_subject_rankings(db: Session, query: SubjectRankingQuery) -> tuple[list[dict], int]:
    """
    多条件查询学科排名

    Returns:
        (排名列表(含关联字段), 总数)
    """
    q = db.query(SubjectRanking).join(School, SubjectRanking.school_id == School.id)

    if query.school_name:
        q = q.filter(School.name.contains(query.school_name))
    if query.school_id:
        q = q.filter(SubjectRanking.school_id == query.school_id)
    if query.major_category:
        q = q.filter(SubjectRanking.major_category == query.major_category)
    if query.ranking_source:
        q = q.filter(SubjectRanking.ranking_source == query.ranking_source)
    if query.ranking_year:
        q = q.filter(SubjectRanking.ranking_year == query.ranking_year)
    if query.grade:
        q = q.filter(SubjectRanking.grade == query.grade)

    total = q.count()
    offset = (query.page - 1) * query.page_size
    rows = (
        q.order_by(
            SubjectRanking.grade.asc().nullslast(),
            SubjectRanking.ranking_position.asc().nullslast(),
        )
        .offset(offset)
        .limit(query.page_size)
        .all()
    )

    results = []
    for row in rows:
        results.append(
            {
                "id": row.id,
                "school_id": row.school_id,
                "school_name": row.school.name if row.school else None,
                "major_category": row.major_category,
                "ranking_source": row.ranking_source,
                "ranking_year": row.ranking_year,
                "ranking_position": row.ranking_position,
                "grade": row.grade,
            }
        )

    return results, total


def get_rankings_by_school(
    db: Session, school_id: int, ranking_source: str | None = None
) -> list[SubjectRanking]:
    """获取某院校的所有学科排名"""
    q = db.query(SubjectRanking).filter(SubjectRanking.school_id == school_id)
    if ranking_source:
        q = q.filter(SubjectRanking.ranking_source == ranking_source)
    return q.order_by(SubjectRanking.major_category).all()
