"""Isolated staging artifacts for audited real admission-data pilots."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.real_data.contracts import (
    AgentCitationMetadata,
    CanonicalAdmissionCandidate,
    Confidence,
    QualityReport,
    build_citation_metadata,
)
from backend.real_data.source_registry import SourcePage, SourceSnapshot


class StagingWriteBlockedError(ValueError):
    """Raised when quality status or lineage prevents staging writes."""


class StagingArtifactReadError(ValueError):
    """Raised when a staging artifact cannot be trusted for readback."""


class StagingArtifact(BaseModel):
    """Metadata for a staged real-data artifact."""

    artifact_path: Path
    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    quality_status: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)


class StagingArtifactPayload(BaseModel):
    """Validated payload read back from an isolated real-data staging artifact."""

    schema_version: Literal["real_data_staging.v1"]
    source_page: SourcePage
    snapshot: SourceSnapshot
    quality_report: QualityReport
    candidates: tuple[CanonicalAdmissionCandidate, ...]
    citations: tuple[AgentCitationMetadata, ...]

    @model_validator(mode="after")
    def validate_artifact_contract(self) -> StagingArtifactPayload:
        if self.quality_report.status == "blocked":
            raise ValueError("blocked quality report cannot be loaded from staging")
        if self.snapshot.source_page_id != self.source_page.source_page_id:
            raise ValueError("snapshot source page does not match source page")
        _validate_staging_inputs(self.candidates, self.snapshot, self.quality_report)
        if len(self.citations) != len(self.candidates):
            raise ValueError("citation count does not match candidates")

        for candidate, citation in zip(self.candidates, self.citations, strict=True):
            expected_citation = build_citation_metadata(candidate, self.source_page, self.snapshot)
            if citation != expected_citation:
                raise ValueError("citation metadata does not match candidate lineage")
        return self


class AdmissionCitationRecord(BaseModel):
    """Agent-facing admission record projected from a validated staging artifact."""

    school_name: str = Field(min_length=1)
    major_or_group_name: str = Field(min_length=1)
    batch: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    min_score: int = Field(ge=0, le=750)
    min_rank: int | None = Field(default=None, ge=1)
    plan_count: int | None = Field(default=None, ge=0)
    raw_row_number: int = Field(ge=1)
    source: str = Field(min_length=1)
    source_type: Literal["official_source_snapshot"] = "official_source_snapshot"
    source_url: str = Field(min_length=1)
    snapshot_url: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    snapshot: str = Field(min_length=1)
    confidence: Confidence
    source_batch_id: str = Field(min_length=1)


def write_admission_staging_artifact(
    *,
    candidates: Sequence[CanonicalAdmissionCandidate],
    source_page: SourcePage,
    snapshot: SourceSnapshot,
    quality_report: QualityReport,
    output_dir: Path,
    overwrite: bool = False,
) -> StagingArtifact:
    """Write canonical candidates and their quality report to an isolated JSON file."""

    _validate_staging_inputs(candidates, snapshot, quality_report)

    artifact_dir = output_dir / snapshot.source_batch_id / snapshot.snapshot_id
    artifact_path = artifact_dir / "admission_candidates.json"
    if artifact_path.exists() and not overwrite:
        raise FileExistsError(f"staging artifact already exists: {artifact_path}")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "real_data_staging.v1",
        "source_page": source_page.model_dump(mode="json"),
        "snapshot": snapshot.model_dump(mode="json"),
        "quality_report": quality_report.model_dump(mode="json"),
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "citations": [
            build_citation_metadata(candidate, source_page, snapshot).model_dump(mode="json")
            for candidate in candidates
        ],
    }

    temp_path = artifact_path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(artifact_path)

    return StagingArtifact(
        artifact_path=artifact_path,
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        quality_status=quality_report.status,
        candidate_count=len(candidates),
    )


def load_admission_staging_artifact(artifact_path: Path) -> StagingArtifactPayload:
    """Read and validate an isolated admission staging artifact."""

    try:
        raw_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        return StagingArtifactPayload.model_validate(raw_payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise StagingArtifactReadError(
            f"invalid staging artifact: {artifact_path}"
        ) from exc


def project_admission_citation_records(
    payload: StagingArtifactPayload,
) -> tuple[AdmissionCitationRecord, ...]:
    """Project validated staging data into future Agent-facing citation records."""

    return tuple(
        AdmissionCitationRecord(
            school_name=candidate.school_name,
            major_or_group_name=candidate.major_or_group_name,
            batch=candidate.batch,
            subject_type=candidate.subject_type,
            min_score=candidate.min_score,
            min_rank=candidate.min_rank,
            plan_count=candidate.plan_count,
            raw_row_number=candidate.raw_row_number,
            source=citation.source,
            source_url=citation.source_url,
            snapshot_url=citation.snapshot_url,
            year=citation.year,
            snapshot=citation.snapshot,
            confidence=citation.confidence,
            source_batch_id=citation.source_batch_id,
        )
        for candidate, citation in zip(payload.candidates, payload.citations, strict=True)
    )


def _validate_staging_inputs(
    candidates: Sequence[CanonicalAdmissionCandidate],
    snapshot: SourceSnapshot,
    quality_report: QualityReport,
) -> None:
    if quality_report.status == "blocked":
        raise StagingWriteBlockedError("blocked quality report cannot be staged")
    if quality_report.source_batch_id != snapshot.source_batch_id:
        raise StagingWriteBlockedError("quality report source batch does not match snapshot")
    if quality_report.snapshot_id != snapshot.snapshot_id:
        raise StagingWriteBlockedError("quality report snapshot does not match snapshot")
    if quality_report.record_count_passed != len(candidates):
        raise StagingWriteBlockedError("quality report passed count does not match candidates")

    for candidate in candidates:
        if candidate.source_batch_id != snapshot.source_batch_id:
            raise StagingWriteBlockedError("candidate source batch does not match snapshot")
        if candidate.snapshot_id != snapshot.snapshot_id:
            raise StagingWriteBlockedError("candidate snapshot does not match snapshot")
