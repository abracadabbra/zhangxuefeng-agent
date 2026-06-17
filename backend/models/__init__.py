"""
数据模型包

导出所有 ORM 模型，方便 Alembic 和其他模块引用
"""

from backend.models.admission_score import AdmissionScore
from backend.models.chat import ChatMessage, ChatSession
from backend.models.enrollment_plan import EnrollmentPlan
from backend.models.feedback import Feedback
from backend.models.major import Major
from backend.models.school import School
from backend.models.subject_ranking import SubjectRanking

__all__ = [
    "School",
    "Major",
    "AdmissionScore",
    "EnrollmentPlan",
    "SubjectRanking",
    "ChatSession",
    "ChatMessage",
    "Feedback",
]
