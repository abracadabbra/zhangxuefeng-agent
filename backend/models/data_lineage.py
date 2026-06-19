"""Real-data source, snapshot, and lineage ORM models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy import String, Text, text
from sqlalchemy.orm import relationship

from backend.database import Base


class DataSourceRecord(Base):
    """Registered official or authorized data source."""

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(100), nullable=False, unique=True, comment="Stable source ID")
    name = Column(String(200), nullable=False, comment="Source display name")
    source_type = Column(String(50), nullable=False, comment="Source type")
    homepage_url = Column(String(500), nullable=False, comment="Source homepage or dataset URL")
    data_categories = Column(Text, nullable=False, comment="JSON array of covered categories")
    coverage = Column(Text, nullable=True, comment="JSON coverage metadata")
    trust_score = Column(Float, nullable=False, comment="Reviewed trust score, 0-1")
    update_frequency = Column(String(50), nullable=False, comment="Expected update cadence")
    collection_method = Column(String(50), nullable=False, comment="Collection method")
    license_note = Column(Text, nullable=False, comment="License and citation notes")
    review_status = Column(
        String(30),
        nullable=False,
        default="candidate",
        server_default="candidate",
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    snapshots = relationship("DataSnapshot", back_populates="source")

    __table_args__ = (
        Index("ix_data_sources_source_id", "source_id"),
        Index("ix_data_sources_source_type", "source_type"),
        Index("ix_data_sources_review_status", "review_status"),
    )


class DataSnapshot(Base):
    """Raw snapshot captured from one registered data source."""

    __tablename__ = "data_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(120), nullable=False, unique=True, comment="Stable snapshot ID")
    source_id = Column(
        String(100),
        ForeignKey("data_sources.source_id"),
        nullable=False,
        comment="Registered source ID",
    )
    dataset = Column(String(80), nullable=False, comment="Dataset name")
    source_url = Column(String(500), nullable=False, comment="Exact source URL")
    published_year = Column(Integer, nullable=False, comment="Data publication year")
    collected_at = Column(DateTime, nullable=False, comment="Snapshot collection timestamp")
    collector = Column(String(50), nullable=False, comment="Collector kind")
    collector_version = Column(String(50), nullable=False, comment="Collector/parser version")
    files = Column(Text, nullable=False, comment="JSON file manifest")
    license_note = Column(Text, nullable=False, comment="Snapshot license/citation note")
    checksum_status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    source = relationship("DataSourceRecord", back_populates="snapshots")
    lineage_records = relationship("DataLineageRecord", back_populates="snapshot")

    __table_args__ = (
        Index("ix_data_snapshots_snapshot_id", "snapshot_id"),
        Index("ix_data_snapshots_source_id", "source_id"),
        Index("ix_data_snapshots_dataset_year", "dataset", "published_year"),
    )


class DataLineageRecord(Base):
    """Link between a canonical row or natural key and its raw snapshot."""

    __tablename__ = "data_lineage_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(80), nullable=False, comment="Canonical entity type")
    entity_id = Column(Integer, nullable=True, comment="Canonical row ID after load")
    natural_key_json = Column(Text, nullable=True, comment="JSON natural key before/after load")
    snapshot_id = Column(
        String(120),
        ForeignKey("data_snapshots.snapshot_id"),
        nullable=False,
        comment="Raw snapshot ID",
    )
    source_record_ref = Column(String(200), nullable=False, comment="Raw row/page/sheet ref")
    parser_name = Column(String(100), nullable=False, comment="Parser name")
    parser_version = Column(String(50), nullable=False, comment="Parser version")
    quality_status = Column(String(30), nullable=False, comment="Quality gate status")
    confidence = Column(Float, nullable=False, comment="Effective confidence, 0-1")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    snapshot = relationship("DataSnapshot", back_populates="lineage_records")

    __table_args__ = (
        Index("ix_data_lineage_entity", "entity_type", "entity_id"),
        Index("ix_data_lineage_snapshot_id", "snapshot_id"),
        Index("ix_data_lineage_quality_status", "quality_status"),
    )
