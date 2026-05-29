"""
数据模型包

导出所有 ORM 模型，方便 Alembic 和其他模块引用
"""
from backend.models.school import School
from backend.models.major import Major
from backend.models.admission_score import AdmissionScore
from backend.models.enrollment_plan import EnrollmentPlan
from backend.models.subject_ranking import SubjectRanking
from backend.models.chat import ChatSession, ChatMessage
from backend.models.feedback import Feedback

__all__ = ["School", "Major", "AdmissionScore", "EnrollmentPlan", "SubjectRanking", "ChatSession", "ChatMessage", "Feedback"]
