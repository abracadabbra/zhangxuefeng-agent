"""
招生计划表 ORM 模型

记录各院校在各省份的招生计划人数和选科要求
"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base


class EnrollmentPlan(Base):
    __tablename__ = "enrollment_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, comment="院校ID")
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False, comment="专业ID")
    province = Column(String(20), nullable=False, comment="招生省份")
    year = Column(Integer, nullable=False, comment="年份")
    plan_count = Column(Integer, nullable=True, comment="计划招生人数")
    subject_requirement = Column(
        String(100),
        nullable=True,
        comment="选科要求: 物理必选/化学必选/不限等",
    )
    batch = Column(String(20), nullable=True, comment="批次")
    duration = Column(Integer, nullable=True, comment="学制（年）")
    tuition = Column(Integer, nullable=True, comment="学费（元/年）")

    # 关联
    school = relationship("School", back_populates="enrollment_plans")
    major = relationship("Major", back_populates="enrollment_plans")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("school_id", "major_id", "province", "year", name="uq_enrollment_plan"),
    )

    def __repr__(self):
        return (
            f"<EnrollmentPlan(school_id={self.school_id}, major_id={self.major_id}, "
            f"province='{self.province}', year={self.year}, plan_count={self.plan_count})>"
        )
