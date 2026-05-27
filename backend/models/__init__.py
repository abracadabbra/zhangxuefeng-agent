"""
数据模型包

导出所有 ORM 模型，方便 Alembic 和其他模块引用
"""
from backend.models.school import School
from backend.models.major import Major
from backend.models.admission_score import AdmissionScore
from backend.models.enrollment_plan import EnrollmentPlan

__all__ = ["School", "Major", "AdmissionScore", "EnrollmentPlan"]
