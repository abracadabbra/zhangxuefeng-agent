"""
专业表 ORM 模型
"""

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Major(Base):
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="专业名称")
    category = Column(String(50), nullable=False, comment="学科门类: 工学/理学/医学/经济学等")
    sub_category = Column(String(50), nullable=True, comment="专业类: 计算机类/电子信息类等")
    employment_rate = Column(Float, nullable=True, comment="就业率 (0-1)")
    avg_salary = Column(Float, nullable=True, comment="毕业五年平均月薪（元）")
    median_salary = Column(Float, nullable=True, comment="毕业五年薪资中位数（元）")
    salary_range = Column(Text, nullable=True, comment="薪资区间 JSON: {low, high}")
    top_industries = Column(Text, nullable=True, comment="主要就业行业 JSON 数组")
    employment_locations = Column(Text, nullable=True, comment="主要就业城市 JSON 数组")
    postgraduate_rate = Column(Float, nullable=True, comment="考研比例 (0-1)")
    overseas_rate = Column(Float, nullable=True, comment="出国比例 (0-1)")
    description = Column(Text, nullable=True, comment="专业介绍")
    job_directions = Column(Text, nullable=True, comment="就业方向（JSON 数组）")
    is_hot = Column(Integer, default=0, comment="是否热门专业: 0否 1是")

    # 关联
    admission_scores = relationship("AdmissionScore", back_populates="major")
    enrollment_plans = relationship("EnrollmentPlan", back_populates="major")

    __table_args__ = (
        Index("ix_majors_category", "category"),
        Index("ix_majors_sub_category", "sub_category"),
    )

    def __repr__(self):
        return f"<Major(id={self.id}, name='{self.name}', category='{self.category}')>"
