"""初始数据模型：院校、专业、分数线、招生计划

Revision ID: 001_initial
Revises:
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 院校表
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("province", sa.String(20), nullable=False),
        sa.Column("city", sa.String(30), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("school_type", sa.String(20), nullable=False),
        sa.Column("ranking", sa.Integer(), nullable=True),
        sa.Column("is_985", sa.Integer(), server_default="0"),
        sa.Column("is_211", sa.Integer(), server_default="0"),
        sa.Column("is_double_first_class", sa.Integer(), server_default="0"),
        sa.Column("website", sa.String(200), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 专业表
    op.create_table(
        "majors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sub_category", sa.String(50), nullable=True),
        sa.Column("employment_rate", sa.Float(), nullable=True),
        sa.Column("avg_salary", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("job_directions", sa.Text(), nullable=True),
        sa.Column("is_hot", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 分数线表
    op.create_table(
        "admission_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("major_id", sa.Integer(), sa.ForeignKey("majors.id"), nullable=True),
        sa.Column("province", sa.String(20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("batch", sa.String(20), nullable=False),
        sa.Column("subject_type", sa.String(10), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=True),
        sa.Column("avg_score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=True),
        sa.Column("min_rank", sa.Integer(), nullable=True),
        sa.Column("plan_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id", "major_id", "province", "year", "batch", "subject_type",
            name="uq_admission_score"
        ),
    )

    # 招生计划表
    op.create_table(
        "enrollment_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("major_id", sa.Integer(), sa.ForeignKey("majors.id"), nullable=False),
        sa.Column("province", sa.String(20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("plan_count", sa.Integer(), nullable=True),
        sa.Column("subject_requirement", sa.String(100), nullable=True),
        sa.Column("batch", sa.String(20), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("tuition", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id", "major_id", "province", "year",
            name="uq_enrollment_plan"
        ),
    )


def downgrade() -> None:
    op.drop_table("enrollment_plans")
    op.drop_table("admission_scores")
    op.drop_table("majors")
    op.drop_table("schools")
