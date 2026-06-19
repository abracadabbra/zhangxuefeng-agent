"""Parser for manually normalized pilot rows.

This parser intentionally accepts already-normalized dictionaries. It is the
first MVP bridge between a reviewed raw snapshot and the quality gate, not a
web crawler or PDF parser.
"""

from typing import Any

from backend.data_pipeline.quality.candidates import (
    CandidateReviewMetadata,
    CandidateSource,
    CanonicalCandidate,
)
from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest


class ManualSampleParser:
    """Parse manually normalized admission score and enrollment plan rows."""

    def parse(self, rows: list[dict], manifest: RawSnapshotManifest) -> list[CanonicalCandidate]:
        return [_parse_row(index, row, manifest) for index, row in enumerate(rows, start=1)]


def _parse_row(
    index: int,
    row: dict[str, Any],
    manifest: RawSnapshotManifest,
) -> CanonicalCandidate:
    dataset = row.get("dataset") or manifest.dataset
    if dataset == "admission_scores":
        return _parse_admission_score(index, row, manifest)
    if dataset == "enrollment_plans":
        return _parse_enrollment_plan(index, row, manifest)
    raise ValueError(f"unsupported manual sample dataset: {dataset}")


def _parse_admission_score(
    index: int,
    row: dict[str, Any],
    manifest: RawSnapshotManifest,
) -> CanonicalCandidate:
    return CanonicalCandidate(
        entity_type="admission_score",
        natural_key={
            "school_name": row.get("school_name"),
            "major_name": row.get("major_name"),
            "province": row.get("province"),
            "year": row.get("year"),
            "batch": row.get("batch"),
            "subject_type": row.get("subject_type"),
        },
        values={
            "min_score": row.get("min_score"),
            "avg_score": row.get("avg_score"),
            "max_score": row.get("max_score"),
            "min_rank": row.get("min_rank"),
            "plan_count": row.get("plan_count"),
        },
        source=_source(index, row, manifest),
    )


def _parse_enrollment_plan(
    index: int,
    row: dict[str, Any],
    manifest: RawSnapshotManifest,
) -> CanonicalCandidate:
    return CanonicalCandidate(
        entity_type="enrollment_plan",
        natural_key={
            "school_name": row.get("school_name"),
            "major_name": row.get("major_name"),
            "province": row.get("province"),
            "year": row.get("year"),
        },
        values={
            "plan_count": row.get("plan_count"),
            "subject_requirement": row.get("subject_requirement"),
            "batch": row.get("batch"),
            "duration": row.get("duration"),
            "tuition": row.get("tuition"),
        },
        source=_source(index, row, manifest),
    )


def _source(index: int, row: dict[str, Any], manifest: RawSnapshotManifest) -> CandidateSource:
    return CandidateSource(
        snapshot_id=manifest.snapshot_id,
        source_record_ref=row.get("source_record_ref") or f"manual_row={index}",
        confidence=row.get("confidence", 0.95),
        review=_review_metadata(row),
    )


def _review_metadata(row: dict[str, Any]) -> CandidateReviewMetadata:
    review = row.get("review")
    if isinstance(review, dict):
        return CandidateReviewMetadata.model_validate(review)

    return CandidateReviewMetadata(
        extracted_by=row.get("extracted_by"),
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        notes=row.get("review_notes") or "",
    )
