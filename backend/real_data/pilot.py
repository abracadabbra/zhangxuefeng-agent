"""Small reviewed-row pilot runner for audited real admission data."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.real_data.contracts import (
    CanonicalAdmissionCandidate,
    QualityIssue,
    QualityReport,
    run_quality_gate,
)
from backend.real_data.parser import (
    AdmissionParseResult,
    AdmissionSchemaReport,
    RawAdmissionRow,
    assess_raw_admission_schema,
    normalize_raw_rows,
)
from backend.real_data.source_registry import SourcePage, SourceSnapshot
from backend.real_data.staging import (
    AdmissionCitationRecord,
    StagingArtifact,
    load_admission_staging_artifact,
    project_admission_citation_records,
    write_admission_staging_artifact,
)


class ReviewedRawRowsArtifactReadError(ValueError):
    """Raised when a reviewed raw rows artifact cannot be trusted."""


class ReviewedRawRowsArtifact(BaseModel):
    """Metadata for a reviewed raw rows artifact."""

    artifact_path: Path
    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    schema_status: str = Field(min_length=1)
    row_count: int = Field(ge=0)


class ReviewedRawRowsPayload(BaseModel):
    """Validated reviewed raw rows before canonical normalization."""

    schema_version: Literal["real_data_reviewed_rows.v1"]
    source_page: SourcePage
    snapshot: SourceSnapshot
    rows: tuple[RawAdmissionRow, ...]
    schema_report: AdmissionSchemaReport

    @model_validator(mode="after")
    def validate_reviewed_rows_contract(self) -> ReviewedRawRowsPayload:
        if self.snapshot.source_page_id != self.source_page.source_page_id:
            raise ValueError("snapshot source page does not match source page")

        for row in self.rows:
            if row.source_batch_id != self.snapshot.source_batch_id:
                raise ValueError("raw row source batch does not match snapshot")
            if row.snapshot_id != self.snapshot.snapshot_id:
                raise ValueError("raw row snapshot does not match snapshot")

        raw_row_numbers = [row.raw_row_number for row in self.rows]
        if len(raw_row_numbers) != len(set(raw_row_numbers)):
            raise ValueError("raw row numbers must be unique within reviewed artifact")

        expected_schema_report = assess_raw_admission_schema(rows=self.rows)
        if not _schema_report_matches(self.schema_report, expected_schema_report):
            raise ValueError("schema report does not match reviewed raw rows")
        return self


class ReviewedAdmissionPilotResult(BaseModel):
    """End-to-end result for a reviewed small-sample admission pilot."""

    source_page: SourcePage
    snapshot: SourceSnapshot
    schema_report: AdmissionSchemaReport
    parse_result: AdmissionParseResult
    quality_report: QualityReport
    artifact: StagingArtifact | None = None
    citation_records: tuple[AdmissionCitationRecord, ...] = ()


def write_reviewed_raw_rows_artifact(
    *,
    rows: Sequence[RawAdmissionRow],
    source_page: SourcePage,
    snapshot: SourceSnapshot,
    output_dir: Path,
    overwrite: bool = False,
) -> ReviewedRawRowsArtifact:
    """Write reviewed raw rows and their schema report to an isolated artifact."""

    payload = ReviewedRawRowsPayload(
        schema_version="real_data_reviewed_rows.v1",
        source_page=source_page,
        snapshot=snapshot,
        rows=tuple(rows),
        schema_report=assess_raw_admission_schema(rows=rows),
    )
    artifact_dir = output_dir / snapshot.source_batch_id / snapshot.snapshot_id
    artifact_path = artifact_dir / "reviewed_raw_rows.json"
    if artifact_path.exists() and not overwrite:
        raise FileExistsError(f"reviewed raw rows artifact already exists: {artifact_path}")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    temp_path = artifact_path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(artifact_path)

    return ReviewedRawRowsArtifact(
        artifact_path=artifact_path,
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        schema_status=payload.schema_report.status,
        row_count=len(rows),
    )


def load_reviewed_raw_rows_artifact(artifact_path: Path) -> ReviewedRawRowsPayload:
    """Read and validate a reviewed raw rows artifact."""

    try:
        raw_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        return ReviewedRawRowsPayload.model_validate(raw_payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ReviewedRawRowsArtifactReadError(
            f"invalid reviewed raw rows artifact: {artifact_path}"
        ) from exc


def run_reviewed_admission_pilot(
    *,
    rows: Sequence[RawAdmissionRow],
    source_page: SourcePage,
    snapshot: SourceSnapshot,
    province: str,
    year: int,
    batch: str,
    subject_type: str,
    output_dir: Path,
    reference_candidates: Sequence[CanonicalAdmissionCandidate] = (),
    expected_schools: tuple[str, ...] = (),
    expected_min_records: int = 1,
    overwrite: bool = False,
) -> ReviewedAdmissionPilotResult:
    """Run reviewed raw rows through schema, quality, staging, and citation projection."""

    schema_report = assess_raw_admission_schema(rows=rows)
    upstream_errors = _schema_quality_issues(schema_report)
    if schema_report.status == "blocked":
        parse_result = AdmissionParseResult(candidates=(), issues=())
    else:
        parse_result = normalize_raw_rows(
            rows=rows,
            province=province,
            year=year,
            batch=batch,
            subject_type=subject_type,
        )
        upstream_errors.extend(_parse_quality_issues(parse_result))

    quality_report = run_quality_gate(
        candidates=list(parse_result.candidates),
        source_page=source_page,
        snapshot=snapshot,
        reference_candidates=reference_candidates,
        expected_schools=expected_schools,
        expected_min_records=expected_min_records,
        upstream_field_errors=upstream_errors,
        upstream_blocked_reasons=tuple(issue.code for issue in upstream_errors),
        record_count_raw=len(rows),
        record_count_parsed=len(parse_result.candidates),
    )
    if quality_report.status == "blocked":
        return ReviewedAdmissionPilotResult(
            source_page=source_page,
            snapshot=snapshot,
            schema_report=schema_report,
            parse_result=parse_result,
            quality_report=quality_report,
        )

    artifact = write_admission_staging_artifact(
        candidates=parse_result.candidates,
        source_page=source_page,
        snapshot=snapshot,
        quality_report=quality_report,
        output_dir=output_dir,
        overwrite=overwrite,
    )
    payload = load_admission_staging_artifact(artifact.artifact_path)
    return ReviewedAdmissionPilotResult(
        source_page=source_page,
        snapshot=snapshot,
        schema_report=schema_report,
        parse_result=parse_result,
        quality_report=quality_report,
        artifact=artifact,
        citation_records=project_admission_citation_records(payload),
    )


def run_reviewed_admission_pilot_from_artifact(
    *,
    reviewed_rows_artifact_path: Path,
    province: str,
    year: int,
    batch: str,
    subject_type: str,
    output_dir: Path,
    reference_candidates: Sequence[CanonicalAdmissionCandidate] = (),
    expected_schools: tuple[str, ...] = (),
    expected_min_records: int = 1,
    overwrite: bool = False,
) -> ReviewedAdmissionPilotResult:
    """Run a reviewed raw rows artifact through the isolated admission pilot."""

    payload = load_reviewed_raw_rows_artifact(reviewed_rows_artifact_path)
    return run_reviewed_admission_pilot(
        rows=payload.rows,
        source_page=payload.source_page,
        snapshot=payload.snapshot,
        province=province,
        year=year,
        batch=batch,
        subject_type=subject_type,
        output_dir=output_dir,
        reference_candidates=reference_candidates,
        expected_schools=expected_schools,
        expected_min_records=expected_min_records,
        overwrite=overwrite,
    )


def _schema_quality_issues(schema_report: AdmissionSchemaReport) -> list[QualityIssue]:
    return [
        QualityIssue(
            level="error",
            code="missing_source_schema_field",
            message=f"source schema is missing required field {field_name}",
        )
        for field_name in schema_report.missing_required_fields
    ]


def _schema_report_matches(
    actual: AdmissionSchemaReport,
    expected: AdmissionSchemaReport,
) -> bool:
    return (
        actual.status == expected.status
        and actual.observed_columns == expected.observed_columns
        and actual.required_fields == expected.required_fields
        and actual.matched_fields == expected.matched_fields
        and actual.missing_required_fields == expected.missing_required_fields
    )


def _parse_quality_issues(parse_result: AdmissionParseResult) -> list[QualityIssue]:
    return [
        QualityIssue(
            level="error",
            code=f"parse_{issue.code}",
            message=issue.message,
            raw_row_number=issue.raw_row_number,
        )
        for issue in parse_result.issues
        if issue.level == "error"
    ]
