"""新增学科排名表

Revision ID: 002_subject_rankings
Revises: 001_initial
Create Date: 2026-05-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_subject_rankings"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subject_rankings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("major_category", sa.String(50), nullable=False, comment="学科门类"),
        sa.Column("ranking_source", sa.String(50), nullable=False, comment="排名来源"),
        sa.Column("ranking_year", sa.Integer(), nullable=False, comment="评估年份"),
        sa.Column("ranking_position", sa.Integer(), nullable=True, comment="排名位次"),
        sa.Column("grade", sa.String(10), nullable=True, comment="评估等级"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id", "major_category", "ranking_source", "ranking_year",
            name="uq_subject_ranking",
        ),
    )


def downgrade() -> None:
    op.drop_table("subject_rankings")
