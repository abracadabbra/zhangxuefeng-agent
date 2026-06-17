"""
学科排名表 ORM 模型

存储教育部学科评估结果（第四轮/第五轮）和第三方排名数据
"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base


class SubjectRanking(Base):
    __tablename__ = "subject_rankings"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "major_category",
            "ranking_source",
            "ranking_year",
            name="uq_subject_ranking",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, comment="院校ID")
    major_category = Column(String(50), nullable=False, comment="学科门类（如：工学、理学、医学）")
    ranking_source = Column(String(50), nullable=False, comment="排名来源")
    ranking_year = Column(Integer, nullable=False, comment="评估年份")
    ranking_position = Column(Integer, nullable=True, comment="排名位次（软科等排名用）")
    grade = Column(String(10), nullable=True, comment="评估等级：A+/A/A-/B+/B/B-/C+/C/C-")

    # 关联
    school = relationship("School", back_populates="subject_rankings")

    def __repr__(self):
        return (
            f"<SubjectRanking(school_id={self.school_id}, "
            f"category='{self.major_category}', grade='{self.grade}')>"
        )
