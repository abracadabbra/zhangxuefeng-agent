"""Format lineage records as Agent/tool source metadata."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.data_pipeline.lineage.service import get_lineage_for_entity
from backend.data_pipeline.lineage.policy import build_answer_source_policy
from backend.models.data_lineage import DataLineageRecord


FRESHNESS_RANK = {
    "current": 0,
    "stale": 1,
    "expired": 2,
    "unknown": 3,
}
APPROVED_REVIEW_STATUSES = {"reviewed", "approved"}


@dataclass(frozen=True)
class SourceMetadataConfig:
    """Runtime options for source metadata formatting."""

    current_year: int = 2026
    current_window_years: int = 1
    stale_window_years: int = 3


def get_sources_for_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
    config: SourceMetadataConfig | None = None,
) -> list[dict]:
    """Return Agent/tool-ready source metadata for one canonical entity."""
    cfg = config or SourceMetadataConfig()
    lineage_records = get_lineage_for_entity(db, entity_type, entity_id)
    return [_format_source(record, cfg) for record in lineage_records]


def summarize_sources(sources: list[dict]) -> dict:
    """Summarize source metadata for Agent answer confidence decisions."""
    best_confidence = _max_numeric(source.get("confidence") for source in sources)
    best_trust_score = _max_numeric(source.get("trust_score") for source in sources)
    freshness = _least_fresh(source.get("freshness") for source in sources)
    source_metadata_complete = _source_metadata_complete(sources)
    review_statuses = sorted(
        {
            str(source.get("review_status"))
            for source in sources
            if source.get("review_status") is not None
        }
    )
    citation_ready = bool(sources)
    needs_caution = (
        not citation_ready
        or not source_metadata_complete
        or best_confidence is None
        or best_trust_score is None
        or freshness != "current"
        or best_confidence < 0.8
        or best_trust_score < 0.8
        or not review_statuses
        or any(status not in APPROVED_REVIEW_STATUSES for status in review_statuses)
    )

    return {
        "source_count": len(sources),
        "citation_ready": citation_ready and source_metadata_complete,
        "needs_caution": needs_caution,
        "source_metadata_complete": source_metadata_complete,
        "best_confidence": best_confidence,
        "best_trust_score": best_trust_score,
        "freshness": freshness,
        "review_statuses": review_statuses,
    }


def _source_metadata_complete(sources: list[dict]) -> bool:
    if not sources:
        return False
    return all(
        bool(source.get("source_id"))
        and bool(source.get("snapshot_id"))
        and isinstance(source.get("published_year"), int)
        and isinstance(source.get("confidence"), int | float)
        for source in sources
    )


def _format_source(record: DataLineageRecord, config: SourceMetadataConfig) -> dict:
    snapshot = record.snapshot
    source = snapshot.source if snapshot else None
    published_year = snapshot.published_year if snapshot else None

    return {
        "source_id": source.source_id if source else None,
        "name": source.name if source else None,
        "source_type": source.source_type if source else None,
        "source_url": snapshot.source_url if snapshot else None,
        "published_year": published_year,
        "snapshot_id": record.snapshot_id,
        "source_record_ref": record.source_record_ref,
        "confidence": record.confidence,
        "freshness": _freshness(published_year, config),
        "quality_status": record.quality_status,
        "trust_score": source.trust_score if source else None,
        "review_status": source.review_status if source else None,
        "license_note": source.license_note if source else None,
    }


def _freshness(published_year: int | None, config: SourceMetadataConfig) -> str:
    if published_year is None:
        return "unknown"

    age = config.current_year - published_year
    if age <= config.current_window_years:
        return "current"
    if age <= config.stale_window_years:
        return "stale"
    return "expired"


def _max_numeric(values: object) -> float | None:
    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, int | float) and not isinstance(value, bool)
    ]
    return max(numeric_values) if numeric_values else None


def _least_fresh(values: object) -> str:
    freshness_values = [
        value for value in values if isinstance(value, str) and value in FRESHNESS_RANK
    ]
    if not freshness_values:
        return "unknown"
    return max(freshness_values, key=lambda value: FRESHNESS_RANK[value])
