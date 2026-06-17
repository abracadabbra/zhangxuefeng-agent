"""
CRUD 操作包

封装所有数据库查询逻辑
"""

from backend.crud.admission_score import (
    get_admission_scores,
    get_score_stats,
    get_scores_by_major,
    get_scores_by_school,
)
from backend.crud.enrollment_plan import (
    get_enrollment_plans,
    get_plans_by_major,
    get_plans_by_school,
)
from backend.crud.major import get_hot_majors, get_major, get_majors, get_majors_by_employment
from backend.crud.school import (
    get_school,
    get_schools,
    get_schools_by_level,
    get_schools_by_province,
)

__all__ = [
    "get_school",
    "get_schools",
    "get_schools_by_province",
    "get_schools_by_level",
    "get_major",
    "get_majors",
    "get_hot_majors",
    "get_majors_by_employment",
    "get_admission_scores",
    "get_scores_by_school",
    "get_scores_by_major",
    "get_score_stats",
    "get_enrollment_plans",
    "get_plans_by_school",
    "get_plans_by_major",
]
