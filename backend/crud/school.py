"""
院校 CRUD 操作
"""

from sqlalchemy.orm import Session

from backend.models.school import School
from backend.schemas.school import SchoolQuery


def get_school(db: Session, school_id: int) -> School | None:
    """根据 ID 获取院校"""
    return db.query(School).filter(School.id == school_id).first()


def get_school_by_name(db: Session, name: str) -> School | None:
    """根据名称精确匹配院校"""
    return db.query(School).filter(School.name == name).first()


def get_schools(db: Session, query: SchoolQuery) -> tuple[list[School], int]:
    """
    多条件查询院校列表

    Returns:
        (院校列表, 总数)
    """
    q = db.query(School)

    if query.name:
        q = q.filter(School.name.contains(query.name))
    if query.province:
        q = q.filter(School.province == query.province)
    if query.level:
        q = q.filter(School.level == query.level)
    if query.school_type:
        q = q.filter(School.school_type == query.school_type)
    if query.is_985 is not None:
        q = q.filter(School.is_985 == query.is_985)
    if query.is_211 is not None:
        q = q.filter(School.is_211 == query.is_211)

    total = q.count()
    offset = (query.page - 1) * query.page_size
    items = q.order_by(School.ranking.asc().nullslast()).offset(offset).limit(query.page_size).all()

    return items, total


def get_schools_by_province(db: Session, province: str) -> list[School]:
    """获取某省份所有院校"""
    return db.query(School).filter(School.province == province).all()


def get_schools_by_level(db: Session, level: str) -> list[School]:
    """获取指定层次院校（985/211/双一流）"""
    return db.query(School).filter(School.level == level).all()
