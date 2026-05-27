"""
专业表 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float, Text
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
    description = Column(Text, nullable=True, comment="专业介绍")
    job_directions = Column(Text, nullable=True, comment="就业方向（JSON 数组）")
    is_hot = Column(Integer, default=0, comment="是否热门专业: 0否 1是")

    # 关联
    admission_scores = relationship("AdmissionScore", back_populates="major")
    enrollment_plans = relationship("EnrollmentPlan", back_populates="major")

    def __repr__(self):
        return f"<Major(id={self.id}, name='{self.name}', category='{self.category}')>"
