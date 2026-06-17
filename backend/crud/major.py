"""
专业 CRUD 操作
"""

from sqlalchemy.orm import Session

from backend.models.major import Major
from backend.schemas.major import MajorQuery


def get_major(db: Session, major_id: int) -> Major | None:
    """根据 ID 获取专业"""
    return db.query(Major).filter(Major.id == major_id).first()


def get_major_by_name(db: Session, name: str) -> Major | None:
    """根据名称精确匹配专业"""
    return db.query(Major).filter(Major.name == name).first()


def get_majors(db: Session, query: MajorQuery) -> tuple[list[Major], int]:
    """
    多条件查询专业列表

    Returns:
        (专业列表, 总数)
    """
    q = db.query(Major)

    if query.name:
        q = q.filter(Major.name.contains(query.name))
    if query.category:
        q = q.filter(Major.category == query.category)
    if query.sub_category:
        q = q.filter(Major.sub_category == query.sub_category)
    if query.is_hot is not None:
        q = q.filter(Major.is_hot == query.is_hot)
    if query.min_employment_rate is not None:
        q = q.filter(Major.employment_rate >= query.min_employment_rate)
    if query.min_avg_salary is not None:
        q = q.filter(Major.avg_salary >= query.min_avg_salary)

    total = q.count()
    offset = (query.page - 1) * query.page_size
    items = (
        q.order_by(Major.avg_salary.desc().nullslast()).offset(offset).limit(query.page_size).all()
    )

    return items, total


def get_hot_majors(db: Session, limit: int = 20) -> list[Major]:
    """获取热门专业"""
    return db.query(Major).filter(Major.is_hot == 1).limit(limit).all()


def get_majors_by_employment(db: Session, min_rate: float = 0.8) -> list[Major]:
    """获取高就业率专业"""
    return (
        db.query(Major)
        .filter(Major.employment_rate >= min_rate)
        .order_by(Major.employment_rate.desc())
        .all()
    )
