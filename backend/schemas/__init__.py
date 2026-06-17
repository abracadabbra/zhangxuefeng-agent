"""
Pydantic 数据模式包

定义 API 请求/响应的数据结构
"""

from backend.schemas.admission_score import AdmissionScoreOut, AdmissionScoreQuery, ScoreStats
from backend.schemas.enrollment_plan import EnrollmentPlanOut, EnrollmentPlanQuery
from backend.schemas.major import MajorOut, MajorQuery
from backend.schemas.school import SchoolOut, SchoolQuery

__all__ = [
    "SchoolOut",
    "SchoolQuery",
    "MajorOut",
    "MajorQuery",
    "AdmissionScoreOut",
    "AdmissionScoreQuery",
    "ScoreStats",
    "EnrollmentPlanOut",
    "EnrollmentPlanQuery",
]
