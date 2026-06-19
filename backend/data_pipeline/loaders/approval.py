"""Loader approval packet helpers.

These helpers create review artifacts only. They do not write canonical tables,
lineage records, raw snapshots, seed data, or RAG indexes.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.data_pipeline.pilots import assert_loader_review_ready
from backend.data_pipeline.quality.candidates import CanonicalCandidate


class LoaderApprovalPacket(BaseModel):
    """Human-reviewable packet required before a canonical loader run."""

    action: str = "canonical_loader_approval"
    load_allowed: bool
    parser_name: str
    parser_version: str
    quality_status: str
    candidate_count: int
    entity_counts: dict[str, int] = Field(default_factory=dict)
    source_id: str | None = None
    snapshot_id: str | None = None
    dataset: str | None = None
    audit_summary: dict[str, Any] = Field(default_factory=dict)
    rollback_actions: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    def to_review_dict(self) -> dict[str, Any]:
        """Return a stable JSON-ready approval packet."""
        return self.model_dump()


def build_loader_approval_packet(
    *,
    audit: dict[str, Any],
    candidates: list[CanonicalCandidate],
    parser_name: str,
    parser_version: str,
    quality_status: str = "passed",
) -> LoaderApprovalPacket:
    """Build a loader approval packet after strict dry-run review checks."""
    assert_loader_review_ready(audit)
    return LoaderApprovalPacket(
        load_allowed=True,
        parser_name=parser_name,
        parser_version=parser_version,
        quality_status=quality_status,
        candidate_count=len(candidates),
        entity_counts=_count_candidates_by_entity(candidates),
        source_id=_optional_str(audit.get("source_id")),
        snapshot_id=_optional_str(audit.get("snapshot_id")),
        dataset=_optional_str(audit.get("dataset")),
        audit_summary=_audit_summary(audit),
        rollback_actions=_rollback_actions(audit, candidates),
        non_goals=_non_goals(),
    )


def _count_candidates_by_entity(candidates: list[CanonicalCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = candidate.entity_type
        counts[key] = counts.get(key, 0) + 1
    return counts


def _audit_summary(audit: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "passed",
        "load_ready",
        "review_status",
        "review_notes",
        "blockers",
        "snapshot_file_issues",
        "source_validation_issues",
        "issue_counts",
        "coverage",
    ]
    return {key: audit.get(key) for key in keys if key in audit}


def _rollback_actions(
    audit: dict[str, Any],
    candidates: list[CanonicalCandidate],
) -> list[str]:
    entity_types = sorted({candidate.entity_type for candidate in candidates})
    snapshot_id = _optional_str(audit.get("snapshot_id")) or "<snapshot_id>"
    return [
        f"Delete lineage records for snapshot_id={snapshot_id}.",
        f"Review canonical rows touched for entity types: {', '.join(entity_types)}.",
        "Re-run Agent/RAG refresh only after rollback review if it was triggered.",
    ]


def _non_goals() -> list[str]:
    return [
        "Does not approve crawler execution.",
        "Does not approve seed data modification.",
        "Does not approve RAG or Agent refresh.",
        "Does not approve production database writes without a separate run command.",
    ]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
