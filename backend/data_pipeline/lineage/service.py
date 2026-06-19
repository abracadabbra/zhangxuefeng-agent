"""Persistence service for data source, snapshot, and lineage records."""

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource
from backend.models.data_lineage import DataLineageRecord, DataSnapshot, DataSourceRecord


def upsert_source(db: Session, source: DataSource) -> DataSourceRecord:
    """Create or update one registered data source."""
    record = get_source(db, source.source_id)
    payload = {
        "name": source.name,
        "source_type": source.source_type,
        "homepage_url": str(source.homepage_url),
        "data_categories": json.dumps(source.data_categories, ensure_ascii=False),
        "coverage": source.coverage.model_dump_json(),
        "trust_score": source.trust_score,
        "update_frequency": source.update_frequency,
        "collection_method": source.collection_method,
        "license_note": source.license_note,
        "review_status": source.review_status,
        "notes": source.notes,
    }

    if record is None:
        record = DataSourceRecord(source_id=source.source_id, **payload)
        db.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)

    db.flush()
    return record


def upsert_snapshot(db: Session, manifest: RawSnapshotManifest) -> DataSnapshot:
    """Create or update one raw snapshot record."""
    record = get_snapshot(db, manifest.snapshot_id)
    payload = {
        "source_id": manifest.source_id,
        "dataset": manifest.dataset,
        "source_url": str(manifest.source_url),
        "published_year": manifest.published_year,
        "collected_at": manifest.collected_at,
        "collector": manifest.collector,
        "collector_version": manifest.collector_version,
        "files": json.dumps([file.model_dump() for file in manifest.files], ensure_ascii=False),
        "license_note": manifest.license_note,
    }

    if record is None:
        record = DataSnapshot(
            snapshot_id=manifest.snapshot_id,
            checksum_status="pending",
            **payload,
        )
        db.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)

    db.flush()
    return record


def create_lineage_record(
    db: Session,
    candidate: CanonicalCandidate,
    *,
    parser_name: str,
    parser_version: str,
    quality_status: str,
    entity_id: int | None = None,
) -> DataLineageRecord:
    """Persist lineage for one candidate row after quality evaluation."""
    record = DataLineageRecord(
        entity_type=candidate.entity_type,
        entity_id=entity_id,
        natural_key_json=_json(candidate.natural_key),
        snapshot_id=candidate.source.snapshot_id,
        source_record_ref=candidate.source.source_record_ref,
        parser_name=parser_name,
        parser_version=parser_version,
        quality_status=quality_status,
        confidence=candidate.source.confidence,
    )
    db.add(record)
    db.flush()
    return record


def get_source(db: Session, source_id: str) -> DataSourceRecord | None:
    """Fetch a source registry record by stable source ID."""
    return db.query(DataSourceRecord).filter(DataSourceRecord.source_id == source_id).first()


def get_snapshot(db: Session, snapshot_id: str) -> DataSnapshot | None:
    """Fetch a raw snapshot record by stable snapshot ID."""
    return db.query(DataSnapshot).filter(DataSnapshot.snapshot_id == snapshot_id).first()


def get_lineage_for_snapshot(db: Session, snapshot_id: str) -> list[DataLineageRecord]:
    """Fetch lineage records produced from a snapshot."""
    return (
        db.query(DataLineageRecord)
        .filter(DataLineageRecord.snapshot_id == snapshot_id)
        .order_by(DataLineageRecord.id.asc())
        .all()
    )


def get_lineage_for_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> list[DataLineageRecord]:
    """Fetch lineage records linked to a canonical entity row."""
    return (
        db.query(DataLineageRecord)
        .filter(
            DataLineageRecord.entity_type == entity_type,
            DataLineageRecord.entity_id == entity_id,
        )
        .order_by(DataLineageRecord.id.asc())
        .all()
    )


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
