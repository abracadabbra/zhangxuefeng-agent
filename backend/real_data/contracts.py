"""Canonical candidates, quality gate, and citation metadata for real data."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.real_data.source_registry import SourcePage, SourceSnapshot, SourceType

Confidence = Literal["high", "medium", "low"]
IssueLevel = Literal["error", "warning"]
QualityStatus = Literal["pass", "warning", "blocked"]


class CanonicalAdmissionCandidate(BaseModel):
    """A normalized admission record that is not production data yet."""

    province: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    school_name: str = Field(min_length=1)
    major_or_group_name: str = Field(min_length=1)
    batch: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    min_score: int = Field(ge=0, le=750)
    min_rank: int | None = Field(default=None, ge=1)
    plan_count: int | None = Field(default=None, ge=0)
    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    raw_row_number: int = Field(ge=1)
    confidence: Confidence
    school_code: str | None = None
    major_code: str | None = None
    selection_requirement: str | None = None
    notes: str | None = None

    def canonical_key(self) -> tuple[str, int, str, str, str, str]:
        """Return the duplicate-detection key for a pilot candidate."""

        return (
            self.province,
            self.year,
            self.school_name,
            self.major_or_group_name,
            self.batch,
            self.subject_type,
        )


class QualityIssue(BaseModel):
    """One quality gate issue tied to a candidate or source snapshot."""

    level: IssueLevel
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    raw_row_number: int | None = Field(default=None, ge=1)


class CoverageMetrics(BaseModel):
    """Small-pilot coverage summary."""

    expected_schools: tuple[str, ...] = ()
    observed_schools: tuple[str, ...] = ()
    missing_schools: tuple[str, ...] = ()
    expected_min_records: int = 0
    observed_records: int = 0


class QualityReport(BaseModel):
    """Structured quality gate output."""

    report_id: str = Field(min_length=1)
    source_batch_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    status: QualityStatus
    record_count_raw: int = Field(ge=0)
    record_count_parsed: int = Field(ge=0)
    record_count_passed: int = Field(ge=0)
    field_errors: tuple[QualityIssue, ...] = ()
    range_errors: tuple[QualityIssue, ...] = ()
    duplicate_conflicts: tuple[QualityIssue, ...] = ()
    cross_source_conflicts: tuple[QualityIssue, ...] = ()
    warning_issues: tuple[QualityIssue, ...] = ()
    coverage_metrics: CoverageMetrics
    freshness_result: str = Field(min_length=1)
    confidence_summary: dict[Confidence, int]
    blocked_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_status_matches_blockers(self) -> QualityReport:
        has_errors = bool(
            self.field_errors
            or self.range_errors
            or self.duplicate_conflicts
            or self.cross_source_conflicts
            or self.blocked_reasons
        )
        if self.status == "blocked" and not has_errors:
            raise ValueError("blocked report must include at least one blocking issue")
        if self.status != "blocked" and self.blocked_reasons:
            raise ValueError("non-blocked report cannot include blocked reasons")
        return self


class AgentCitationMetadata(BaseModel):
    """Metadata future Agent tools should attach to real-data answers."""

    source: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    snapshot_url: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    snapshot: str = Field(min_length=1)
    confidence: Confidence
    source_batch_id: str = Field(min_length=1)


def build_citation_metadata(
    candidate: CanonicalAdmissionCandidate,
    source_page: SourcePage,
    snapshot: SourceSnapshot,
) -> AgentCitationMetadata:
    """Project a candidate into future Agent-facing citation metadata."""

    if snapshot.source_page_id != source_page.source_page_id:
        raise ValueError("snapshot source page does not match source page")
    if candidate.source_batch_id != snapshot.source_batch_id:
        raise ValueError("candidate source batch does not match snapshot")
    if candidate.snapshot_id != snapshot.snapshot_id:
        raise ValueError("candidate snapshot does not match snapshot")

    return AgentCitationMetadata(
        source=source_page.source_name,
        source_url=source_page.source_url,
        snapshot_url=snapshot.raw_file_url,
        year=candidate.year,
        snapshot=candidate.snapshot_id,
        confidence=candidate.confidence,
        source_batch_id=candidate.source_batch_id,
    )


def run_quality_gate(
    *,
    candidates: list[CanonicalAdmissionCandidate],
    source_page: SourcePage,
    snapshot: SourceSnapshot,
    reference_candidates: Sequence[CanonicalAdmissionCandidate] = (),
    allowed_source_types: Sequence[SourceType] = (
        "official_exam_authority",
        "authorized_partner",
    ),
    expected_schools: tuple[str, ...] = (),
    expected_min_records: int = 1,
    upstream_field_errors: Sequence[QualityIssue] = (),
    upstream_blocked_reasons: Sequence[str] = (),
    record_count_raw: int | None = None,
    record_count_parsed: int | None = None,
) -> QualityReport:
    """Run the first pilot quality gate before any staging or DB write."""

    field_errors: list[QualityIssue] = list(upstream_field_errors)
    range_errors: list[QualityIssue] = []
    duplicate_conflicts: list[QualityIssue] = []
    cross_source_conflicts: list[QualityIssue] = []
    blocked_reasons: list[str] = list(upstream_blocked_reasons)
    warning_issues: list[QualityIssue] = []
    confidence_summary: dict[Confidence, int] = {"high": 0, "medium": 0, "low": 0}

    if not candidates:
        blocked_reasons.append("no parsed candidates")
    if snapshot.source_page_id != source_page.source_page_id:
        field_errors.append(
            QualityIssue(
                level="error",
                code="snapshot_source_page_mismatch",
                message="snapshot source page does not match source page",
            )
        )
    if source_page.source_type not in allowed_source_types:
        field_errors.append(
            QualityIssue(
                level="error",
                code="source_type_not_allowed",
                message=(
                    "source type is not allowed for this quality gate: "
                    f"{source_page.source_type}"
                ),
            )
        )
    if (
        source_page.published_at is not None
        and snapshot.captured_at.date() < source_page.published_at
    ):
        field_errors.append(
            QualityIssue(
                level="error",
                code="snapshot_captured_before_publish",
                message="snapshot capture date is before source publish date",
            )
        )

    seen_keys: dict[tuple[str, int, str, str, str, str], int] = {}
    reference_by_key = {
        reference.canonical_key(): reference for reference in reference_candidates
    }
    observed_schools = tuple(sorted({candidate.school_name for candidate in candidates}))

    for candidate in candidates:
        confidence_summary[candidate.confidence] += 1
        if candidate.source_batch_id != snapshot.source_batch_id:
            field_errors.append(
                QualityIssue(
                    level="error",
                    code="source_batch_mismatch",
                    message="candidate source batch does not match snapshot",
                    raw_row_number=candidate.raw_row_number,
                )
            )
        if candidate.snapshot_id != snapshot.snapshot_id:
            field_errors.append(
                QualityIssue(
                    level="error",
                    code="snapshot_mismatch",
                    message="candidate snapshot does not match source snapshot",
                    raw_row_number=candidate.raw_row_number,
                )
            )
        if candidate.year != source_page.year:
            range_errors.append(
                QualityIssue(
                    level="error",
                    code="year_mismatch",
                    message="candidate year does not match source page year",
                    raw_row_number=candidate.raw_row_number,
                )
            )
        if candidate.province != source_page.province:
            field_errors.append(
                QualityIssue(
                    level="error",
                    code="province_mismatch",
                    message="candidate province does not match source page province",
                    raw_row_number=candidate.raw_row_number,
                )
            )
        if candidate.confidence == "low":
            blocked_reasons.append(f"low confidence row {candidate.raw_row_number}")
        if candidate.confidence == "medium":
            warning_issues.append(
                QualityIssue(
                    level="warning",
                    code="medium_confidence_row",
                    message="candidate has medium confidence and requires review",
                    raw_row_number=candidate.raw_row_number,
                )
            )

        key = candidate.canonical_key()
        if key in seen_keys:
            duplicate_conflicts.append(
                QualityIssue(
                    level="error",
                    code="duplicate_canonical_key",
                    message=f"duplicate candidate key first seen at row {seen_keys[key]}",
                    raw_row_number=candidate.raw_row_number,
                )
            )
        else:
            seen_keys[key] = candidate.raw_row_number
        reference = reference_by_key.get(key)
        if reference is not None and _has_cross_source_conflict(candidate, reference):
            changed_fields = ", ".join(_changed_conflict_fields(candidate, reference))
            cross_source_conflicts.append(
                QualityIssue(
                    level="error",
                    code="cross_source_conflict",
                    message=(
                        "candidate conflicts with reference "
                        f"{reference.source_batch_id}/{reference.snapshot_id} "
                        f"on {changed_fields}"
                    ),
                    raw_row_number=candidate.raw_row_number,
                )
            )

    missing_schools = tuple(sorted(set(expected_schools) - set(observed_schools)))
    if missing_schools:
        warning_issues.append(
            QualityIssue(
                level="warning",
                code="pilot_school_coverage_gap",
                message=f"missing pilot schools: {', '.join(missing_schools)}",
            )
        )
    if len(candidates) < expected_min_records:
        warning_issues.append(
            QualityIssue(
                level="warning",
                code="record_coverage_gap",
                message="parsed candidate count is below pilot expectation",
            )
        )

    if source_page.published_at and source_page.published_at.year == source_page.year:
        freshness_result = "published_in_admission_year"
    else:
        freshness_result = "published_date_missing_or_outside_admission_year"
        warning_issues.append(
            QualityIssue(
                level="warning",
                code="freshness_warning",
                message="source publish date is missing or outside admission year",
            )
        )

    errors = (
        field_errors
        or range_errors
        or duplicate_conflicts
        or cross_source_conflicts
        or blocked_reasons
    )
    if errors:
        status: QualityStatus = "blocked"
    elif warning_issues or confidence_summary["medium"] > 0:
        status = "warning"
    else:
        status = "pass"

    return QualityReport(
        report_id=f"{snapshot.snapshot_id}-quality",
        source_batch_id=snapshot.source_batch_id,
        snapshot_id=snapshot.snapshot_id,
        status=status,
        record_count_raw=len(candidates) if record_count_raw is None else record_count_raw,
        record_count_parsed=len(candidates) if record_count_parsed is None else record_count_parsed,
        record_count_passed=0 if status == "blocked" else len(candidates),
        field_errors=tuple(field_errors),
        range_errors=tuple(range_errors),
        duplicate_conflicts=tuple(duplicate_conflicts),
        cross_source_conflicts=tuple(cross_source_conflicts),
        warning_issues=tuple(warning_issues),
        coverage_metrics=CoverageMetrics(
            expected_schools=expected_schools,
            observed_schools=observed_schools,
            missing_schools=missing_schools,
            expected_min_records=expected_min_records,
            observed_records=len(candidates),
        ),
        freshness_result=freshness_result,
        confidence_summary=confidence_summary,
        blocked_reasons=tuple(blocked_reasons),
    )


def _has_cross_source_conflict(
    candidate: CanonicalAdmissionCandidate,
    reference: CanonicalAdmissionCandidate,
) -> bool:
    if (
        candidate.source_batch_id == reference.source_batch_id
        and candidate.snapshot_id == reference.snapshot_id
    ):
        return False
    return bool(_changed_conflict_fields(candidate, reference))


def _changed_conflict_fields(
    candidate: CanonicalAdmissionCandidate,
    reference: CanonicalAdmissionCandidate,
) -> tuple[str, ...]:
    changed_fields: list[str] = []
    for field_name in ("min_score", "min_rank", "plan_count"):
        if getattr(candidate, field_name) != getattr(reference, field_name):
            changed_fields.append(field_name)
    return tuple(changed_fields)
