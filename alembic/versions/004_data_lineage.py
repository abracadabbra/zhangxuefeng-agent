"""Add real-data source, snapshot, and lineage tables.

Revision ID: 004_data_lineage
Revises: 003_extend_major_employment
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_data_lineage"
down_revision: str | None = "003_extend_major_employment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("homepage_url", sa.String(500), nullable=False),
        sa.Column("data_categories", sa.Text(), nullable=False),
        sa.Column("coverage", sa.Text(), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("update_frequency", sa.String(50), nullable=False),
        sa.Column("collection_method", sa.String(50), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.Column(
            "review_status",
            sa.String(30),
            server_default="candidate",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", name="uq_data_sources_source_id"),
    )
    op.create_index("ix_data_sources_source_id", "data_sources", ["source_id"])
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"])
    op.create_index("ix_data_sources_review_status", "data_sources", ["review_status"])

    op.create_table(
        "data_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(120), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("dataset", sa.String(80), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("published_year", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("collector", sa.String(50), nullable=False),
        sa.Column("collector_version", sa.String(50), nullable=False),
        sa.Column("files", sa.Text(), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.Column(
            "checksum_status",
            sa.String(30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.source_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", name="uq_data_snapshots_snapshot_id"),
    )
    op.create_index("ix_data_snapshots_snapshot_id", "data_snapshots", ["snapshot_id"])
    op.create_index("ix_data_snapshots_source_id", "data_snapshots", ["source_id"])
    op.create_index(
        "ix_data_snapshots_dataset_year",
        "data_snapshots",
        ["dataset", "published_year"],
    )

    op.create_table(
        "data_lineage_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("natural_key_json", sa.Text(), nullable=True),
        sa.Column("snapshot_id", sa.String(120), nullable=False),
        sa.Column("source_record_ref", sa.String(200), nullable=False),
        sa.Column("parser_name", sa.String(100), nullable=False),
        sa.Column("parser_version", sa.String(50), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["snapshot_id"], ["data_snapshots.snapshot_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_lineage_entity",
        "data_lineage_records",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_data_lineage_snapshot_id",
        "data_lineage_records",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_data_lineage_quality_status",
        "data_lineage_records",
        ["quality_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_lineage_quality_status", table_name="data_lineage_records")
    op.drop_index("ix_data_lineage_snapshot_id", table_name="data_lineage_records")
    op.drop_index("ix_data_lineage_entity", table_name="data_lineage_records")
    op.drop_table("data_lineage_records")

    op.drop_index("ix_data_snapshots_dataset_year", table_name="data_snapshots")
    op.drop_index("ix_data_snapshots_source_id", table_name="data_snapshots")
    op.drop_index("ix_data_snapshots_snapshot_id", table_name="data_snapshots")
    op.drop_table("data_snapshots")

    op.drop_index("ix_data_sources_review_status", table_name="data_sources")
    op.drop_index("ix_data_sources_source_type", table_name="data_sources")
    op.drop_index("ix_data_sources_source_id", table_name="data_sources")
    op.drop_table("data_sources")
