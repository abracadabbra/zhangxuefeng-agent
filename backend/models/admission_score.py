"""
录取分数线表 ORM 模型

核心四元组: (school, major, province, year)
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.database import Base


class AdmissionScore(Base):
    __tablename__ = "admission_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, comment="院校ID")
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=True, comment="专业ID（可为空表示院校分数线）")
    province = Column(String(20), nullable=False, comment="招生省份")
    year = Column(Integer, nullable=False, comment="年份")
    batch = Column(String(20), nullable=False, comment="批次: 本科一批/本科二批/提前批/专科")
    subject_type = Column(String(10), nullable=False, comment="科类: 理工/文史/综合/物理类/历史类")
    min_score = Column(Integer, nullable=True, comment="最低分")
    avg_score = Column(Float, nullable=True, comment="平均分")
    max_score = Column(Integer, nullable=True, comment="最高分")
    min_rank = Column(Integer, nullable=True, comment="最低位次")
    plan_count = Column(Integer, nullable=True, comment="招生人数")

    # 关联
    school = relationship("School", back_populates="admission_scores")
    major = relationship("Major", back_populates="admission_scores")

    # 唯一约束: 同一学校、专业、省份、年份、批次、科类只有一条记录
    __table_args__ = (
        UniqueConstraint(
            "school_id", "major_id", "province", "year", "batch", "subject_type",
            name="uq_admission_score"
        ),
    )

    def __repr__(self):
        return (
            f"<AdmissionScore(school_id={self.school_id}, major_id={self.major_id}, "
            f"province='{self.province}', year={self.year}, min_score={self.min_score})>"
        )
