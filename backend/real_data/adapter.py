"""Read-only adapters for validated real admission-data staging artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from backend.real_data.manifest import iter_manifest_artifact_paths
from backend.real_data.staging import (
    AdmissionCitationRecord,
    load_admission_staging_artifact,
    project_admission_citation_records,
)


class ApprovalRequiredError(ValueError):
    """Raised when approval status prevents read-only real-data consumption."""


class AdmissionQuery(BaseModel):
    """Small read-only query shape for validated admission staging artifacts."""

    province: str | None = Field(default=None, min_length=1)
    year: int | None = Field(default=None, ge=2000, le=2100)
    school_name: str | None = Field(default=None, min_length=1)
    major_keyword: str | None = Field(default=None, min_length=1)
    batch: str | None = Field(default=None, min_length=1)
    subject_type: str | None = Field(default=None, min_length=1)
    min_score_at_least: int | None = Field(default=None, ge=0, le=750)
    min_score_at_most: int | None = Field(default=None, ge=0, le=750)

    @model_validator(mode="after")
    def validate_score_bounds(self) -> AdmissionQuery:
        if (
            self.min_score_at_least is not None
            and self.min_score_at_most is not None
            and self.min_score_at_least > self.min_score_at_most
        ):
            raise ValueError("min_score_at_least cannot exceed min_score_at_most")
        return self


class AdmissionQueryResult(BaseModel):
    """Records returned from an isolated read-only real-data adapter."""

    records: tuple[AdmissionCitationRecord, ...]
    total: int = Field(ge=0)


def query_admission_records_from_staging(
    artifact_path: Path,
    query: AdmissionQuery,
) -> AdmissionQueryResult:
    """Query validated staging data without touching DB, seeds, or Agent tools."""

    payload = load_admission_staging_artifact(artifact_path)
    records = tuple(
        record
        for record in project_admission_citation_records(payload)
        if _matches_query(record, payload.source_page.province, query)
    )
    return AdmissionQueryResult(records=records, total=len(records))


def query_admission_records_from_manifest(
    manifest_path: Path,
    query: AdmissionQuery,
) -> AdmissionQueryResult:
    """Query all trusted artifacts registered in a staging manifest."""

    records = tuple(
        record
        for artifact_path in iter_manifest_artifact_paths(manifest_path)
        for record in query_admission_records_from_staging(artifact_path, query).records
    )
    return AdmissionQueryResult(records=records, total=len(records))


def query_admission_records_from_approval(
    approval_path: Path,
    query: AdmissionQuery,
) -> AdmissionQueryResult:
    """Query records only after a manual approval artifact has been verified."""

    from backend.real_data.approval import load_manual_approval_artifact

    approval = load_manual_approval_artifact(approval_path)
    if approval.decision != "approved":
        raise ApprovalRequiredError("manual approval decision is not approved")
    manifest_path = approval.manifest_path
    if not manifest_path.is_absolute():
        manifest_path = approval_path.parent / manifest_path
    return query_admission_records_from_manifest(manifest_path, query)


def _matches_query(
    record: AdmissionCitationRecord,
    province: str,
    query: AdmissionQuery,
) -> bool:
    if query.province is not None and province != query.province:
        return False
    if query.year is not None and record.year != query.year:
        return False
    if query.school_name is not None and record.school_name != query.school_name:
        return False
    if query.major_keyword is not None and query.major_keyword not in record.major_or_group_name:
        return False
    if query.batch is not None and record.batch != query.batch:
        return False
    if query.subject_type is not None and record.subject_type != query.subject_type:
        return False
    if query.min_score_at_least is not None and record.min_score < query.min_score_at_least:
        return False
    if query.min_score_at_most is not None and record.min_score > query.min_score_at_most:
        return False
    return True
