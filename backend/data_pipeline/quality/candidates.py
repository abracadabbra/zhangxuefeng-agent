"""Canonical candidate row contracts before database loading."""

from typing import Any, Literal

from pydantic import BaseModel, Field


EntityType = Literal["admission_score", "enrollment_plan"]


class CandidateReviewMetadata(BaseModel):
    """Human review fields attached to a manually prepared candidate row."""

    extracted_by: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    notes: str = ""


class CandidateSource(BaseModel):
    """Lineage fields attached to a parser-produced candidate row."""

    snapshot_id: str = Field(min_length=1)
    source_record_ref: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    review: CandidateReviewMetadata = Field(default_factory=CandidateReviewMetadata)


class CanonicalCandidate(BaseModel):
    """A parsed row candidate that has not yet passed quality checks."""

    entity_type: EntityType
    natural_key: dict[str, Any] = Field(default_factory=dict)
    values: dict[str, Any] = Field(default_factory=dict)
    source: CandidateSource
