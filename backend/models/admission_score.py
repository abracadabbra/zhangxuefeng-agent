"""
录取分数线表 ORM 模型

核心四元组: (school, major_label, province, year, batch, subject_type)
"""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base


class AdmissionScore(Base):
    __tablename__ = "admission_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, comment="院校ID")
    major_id = Column(
        Integer,
        ForeignKey("majors.id"),
        nullable=True,
        comment="标准专业ID（可为空表示未匹配标准专业）",
    )
    major_label = Column(
        String(200),
        nullable=True,
        comment="投档单位标签（原始名称，含方向/班级；与 major_id 不同时存在时存此字段）",
    )
    province = Column(String(20), nullable=False, comment="招生省份")
    year = Column(Integer, nullable=False, comment="年份")
    batch = Column(String(20), nullable=False, comment="批次: 一段/二段/本科一批/本科二批/专科")
    subject_type = Column(String(10), nullable=True, comment="科类: 理工/文史/综合/物理类/历史类（新高考省份可为空）")
    min_score = Column(Integer, nullable=True, comment="最低分")
    avg_score = Column(Float, nullable=True, comment="平均分")
    max_score = Column(Integer, nullable=True, comment="最高分")
    min_rank = Column(Integer, nullable=True, comment="最低位次")
    plan_count = Column(Integer, nullable=True, comment="招生人数")

    # 关联
    school = relationship("School", back_populates="admission_scores")
    major = relationship("Major", back_populates="admission_scores")

    # 唯一约束: 同一学校、投档单位、省份、年份、批次、科类只有一条记录
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "major_id",
            "major_label",
            "province",
            "year",
            "batch",
            "subject_type",
            name="uq_admission_score",
        ),
        Index("ix_admission_scores_school_id", "school_id"),
        Index("ix_admission_scores_province", "province"),
        Index("ix_admission_scores_year", "year"),
        Index("ix_admission_scores_school_province_year", "school_id", "province", "year"),
    )

    def __repr__(self):
        return (
            f"<AdmissionScore(school_id={self.school_id}, major_label='{self.major_label}', "
            f"province='{self.province}', year={self.year}, batch='{self.batch}', "
            f"min_score={self.min_score})>"
        )
