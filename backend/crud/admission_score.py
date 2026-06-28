"""
录取分数线 CRUD 操作

核心查询维度: (school, major_label, province, year, batch)
"""

from typing import Any, cast

from sqlalchemy.orm import Session

from backend.models.admission_score import AdmissionScore
from backend.models.major import Major
from backend.models.school import School
from backend.schemas.admission_score import AdmissionScoreQuery, ScoreStats


def get_admission_scores(db: Session, query: AdmissionScoreQuery) -> tuple[list[dict], int]:
    """
    多条件查询录取分数线

    支持按学校名/投档单位/省份/年份/分数范围等组合查询

    Returns:
        (分数线列表(含关联字段), 总数)
    """
    q = db.query(AdmissionScore).join(School, AdmissionScore.school_id == School.id)
    q = q.outerjoin(Major, AdmissionScore.major_id == Major.id)

    # 学校筛选
    if query.school_name:
        q = q.filter(School.name.contains(query.school_name))
    if query.school_id:
        q = q.filter(AdmissionScore.school_id == query.school_id)

    # 投档单位筛选（按 major_label 模糊匹配）
    if query.major_name:
        q = q.filter(AdmissionScore.major_label.contains(query.major_name))
    if query.major_id:
        q = q.filter(AdmissionScore.major_id == query.major_id)

    # 省份筛选
    if query.province:
        q = q.filter(AdmissionScore.province == query.province)

    # 年份筛选
    if query.year:
        q = q.filter(AdmissionScore.year == query.year)
    if query.year_from:
        q = q.filter(AdmissionScore.year >= query.year_from)
    if query.year_to:
        q = q.filter(AdmissionScore.year <= query.year_to)

    # 批次和科类
    if query.batch:
        q = q.filter(AdmissionScore.batch == query.batch)
    if query.subject_type:
        q = q.filter(AdmissionScore.subject_type == query.subject_type)

    # 分数范围
    if query.min_score_floor is not None:
        q = q.filter(AdmissionScore.min_score >= query.min_score_floor)
    if query.max_score_ceil is not None:
        q = q.filter(AdmissionScore.min_score <= query.max_score_ceil)

    total = q.count()
    offset = (query.page - 1) * query.page_size
    rows = (
        q.order_by(AdmissionScore.year.desc(), AdmissionScore.min_score.desc())
        .offset(offset)
        .limit(query.page_size)
        .all()
    )

    # 转换为带关联字段的 dict
    results = []
    for row in rows:
        d = {
            "id": row.id,
            "school_id": row.school_id,
            "major_id": row.major_id,
            "major_label": row.major_label,
            "province": row.province,
            "year": row.year,
            "batch": row.batch,
            "subject_type": row.subject_type,
            "min_score": row.min_score,
            "avg_score": row.avg_score,
            "max_score": row.max_score,
            "min_rank": row.min_rank,
            "plan_count": row.plan_count,
            "school_name": row.school.name if row.school else None,
            "major_name": row.major.name if row.major else None,
        }
        results.append(d)

    return results, total


def get_scores_by_school(
    db: Session, school_id: int, province: str | None = None, year: int | None = None
) -> list[AdmissionScore]:
    """获取某院校的分数线"""
    q = db.query(AdmissionScore).filter(AdmissionScore.school_id == school_id)
    if province:
        q = q.filter(AdmissionScore.province == province)
    if year:
        q = q.filter(AdmissionScore.year == year)
    return q.order_by(AdmissionScore.year.desc()).all()


def get_scores_by_major(
    db: Session, major_id: int, province: str | None = None, year: int | None = None
) -> list[AdmissionScore]:
    """获取某专业的分数线（跨院校）"""
    q = db.query(AdmissionScore).filter(AdmissionScore.major_id == major_id)
    if province:
        q = q.filter(AdmissionScore.province == province)
    if year:
        q = q.filter(AdmissionScore.year == year)
    return q.order_by(AdmissionScore.min_score.desc()).all()


def get_score_stats(
    db: Session, school_id: int, major_id: int | None, province: str, year: int
) -> ScoreStats | None:
    """获取分数统计信息"""
    q = db.query(AdmissionScore).filter(
        AdmissionScore.school_id == school_id,
        AdmissionScore.province == province,
        AdmissionScore.year == year,
    )
    if major_id:
        q = q.filter(AdmissionScore.major_id == major_id)

    rows = cast(list[Any], q.all())
    if not rows:
        return None

    school = cast(Any, db.query(School).filter(School.id == school_id).first())
    major = cast(Any, db.query(Major).filter(Major.id == major_id).first()) if major_id else None

    scores = [r.min_score for r in rows if r.min_score is not None]
    avg_scores = [r.avg_score for r in rows if r.avg_score is not None]
    ranks = [r.min_rank for r in rows if r.min_rank is not None]

    return ScoreStats(
        school_name=school.name if school else "",
        major_name=major.name if major else None,
        province=province,
        year=year,
        min_score=min(scores) if scores else None,
        avg_score=round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else None,
        max_score=max(scores) if scores else None,
        min_rank=min(ranks) if ranks else None,
        score_count=len(rows),
    )