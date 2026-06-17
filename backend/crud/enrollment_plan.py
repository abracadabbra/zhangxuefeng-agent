"""
招生计划 CRUD 操作
"""

from sqlalchemy.orm import Session

from backend.models.enrollment_plan import EnrollmentPlan
from backend.models.major import Major
from backend.models.school import School
from backend.schemas.enrollment_plan import EnrollmentPlanQuery


def get_enrollment_plans(db: Session, query: EnrollmentPlanQuery) -> tuple[list[dict], int]:
    """
    多条件查询招生计划

    Returns:
        (招生计划列表(含关联字段), 总数)
    """
    q = db.query(EnrollmentPlan).join(School, EnrollmentPlan.school_id == School.id)
    q = q.join(Major, EnrollmentPlan.major_id == Major.id)

    if query.school_name:
        q = q.filter(School.name.contains(query.school_name))
    if query.school_id:
        q = q.filter(EnrollmentPlan.school_id == query.school_id)
    if query.major_name:
        q = q.filter(Major.name.contains(query.major_name))
    if query.major_id:
        q = q.filter(EnrollmentPlan.major_id == query.major_id)
    if query.province:
        q = q.filter(EnrollmentPlan.province == query.province)
    if query.year:
        q = q.filter(EnrollmentPlan.year == query.year)

    total = q.count()
    offset = (query.page - 1) * query.page_size
    rows = q.order_by(EnrollmentPlan.year.desc()).offset(offset).limit(query.page_size).all()

    results = []
    for row in rows:
        d = {
            "id": row.id,
            "school_id": row.school_id,
            "major_id": row.major_id,
            "province": row.province,
            "year": row.year,
            "plan_count": row.plan_count,
            "subject_requirement": row.subject_requirement,
            "batch": row.batch,
            "duration": row.duration,
            "tuition": row.tuition,
            "school_name": row.school.name if row.school else None,
            "major_name": row.major.name if row.major else None,
        }
        results.append(d)

    return results, total


def get_plans_by_school(
    db: Session, school_id: int, province: str | None = None, year: int | None = None
) -> list[EnrollmentPlan]:
    """获取某院校的招生计划"""
    q = db.query(EnrollmentPlan).filter(EnrollmentPlan.school_id == school_id)
    if province:
        q = q.filter(EnrollmentPlan.province == province)
    if year:
        q = q.filter(EnrollmentPlan.year == year)
    return q.all()


def get_plans_by_major(
    db: Session, major_id: int, province: str | None = None, year: int | None = None
) -> list[EnrollmentPlan]:
    """获取某专业的招生计划（跨院校）"""
    q = db.query(EnrollmentPlan).filter(EnrollmentPlan.major_id == major_id)
    if province:
        q = q.filter(EnrollmentPlan.province == province)
    if year:
        q = q.filter(EnrollmentPlan.year == year)
    return q.all()
