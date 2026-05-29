"""扩展 Major 表就业数据字段

Revision ID: 003_extend_major_employment
Revises: 002_subject_rankings
Create Date: 2026-05-28
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_extend_major_employment"
down_revision: str | None = "002_subject_rankings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tbl = "majors"
    op.add_column(tbl, sa.Column("median_salary", sa.Float(), nullable=True))
    op.add_column(tbl, sa.Column("salary_range", sa.Text(), nullable=True))
    op.add_column(tbl, sa.Column("top_industries", sa.Text(), nullable=True))
    op.add_column(tbl, sa.Column("employment_locations", sa.Text(), nullable=True))
    op.add_column(tbl, sa.Column("postgraduate_rate", sa.Float(), nullable=True))
    op.add_column(tbl, sa.Column("overseas_rate", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("majors", "overseas_rate")
    op.drop_column("majors", "postgraduate_rate")
    op.drop_column("majors", "employment_locations")
    op.drop_column("majors", "top_industries")
    op.drop_column("majors", "salary_range")
    op.drop_column("majors", "median_salary")
