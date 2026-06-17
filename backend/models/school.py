"""
院校表 ORM 模型
"""

from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="院校名称")
    province = Column(String(20), nullable=False, comment="所在省份")
    city = Column(String(30), nullable=False, comment="所在城市")
    level = Column(String(20), nullable=False, comment="层次: 985/211/双一流/普通")
    school_type = Column(String(20), nullable=False, comment="类型: 综合/理工/医药/师范/财经等")
    ranking = Column(Integer, nullable=True, comment="软科排名（可为空）")
    is_985 = Column(Integer, default=0, comment="是否985: 0否 1是")
    is_211 = Column(Integer, default=0, comment="是否211: 0否 1是")
    is_double_first_class = Column(Integer, default=0, comment="是否双一流: 0否 1是")
    website = Column(String(200), nullable=True, comment="官网地址")
    description = Column(String(500), nullable=True, comment="院校简介")

    # 关联
    admission_scores = relationship("AdmissionScore", back_populates="school")
    enrollment_plans = relationship("EnrollmentPlan", back_populates="school")
    subject_rankings = relationship("SubjectRanking", back_populates="school")

    __table_args__ = (
        Index("ix_schools_province", "province"),
        Index("ix_schools_level", "level"),
        Index("ix_schools_is_985", "is_985"),
        Index("ix_schools_is_211", "is_211"),
    )

    def __repr__(self):
        return f"<School(id={self.id}, name='{self.name}', level='{self.level}')>"
