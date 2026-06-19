"""Quality gate checks for canonical candidate rows."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.data_pipeline.quality.report import QualityIssue, QualityReport


REQUIRED_NATURAL_KEYS = {
    "admission_score": ["school_name", "province", "year", "batch", "subject_type"],
    "enrollment_plan": ["school_name", "major_name", "province", "year"],
}

SCORE_FIELDS = ["min_score", "avg_score", "max_score"]


class QualityGateConfig(BaseModel):
    """Runtime thresholds for candidate quality checks."""

    model_config = ConfigDict(frozen=True)

    current_year: int = 2026
    freshness_window_years: int = 1
    min_agent_confidence: float = 0.8
    expected_provinces: tuple[str, ...] = ()
    expected_years: tuple[int, ...] = ()
    require_review_metadata: bool = False


def run_quality_gate(
    candidates: list[CanonicalCandidate],
    config: QualityGateConfig | None = None,
) -> QualityReport:
    """Run deterministic MVP quality checks on parser-produced candidates."""
    cfg = config or QualityGateConfig()
    issues: list[QualityIssue] = []

    for index, candidate in enumerate(candidates):
        issues.extend(_check_required_fields(index, candidate))
        issues.extend(_check_ranges(index, candidate))
        issues.extend(_check_freshness(index, candidate, cfg))
        issues.extend(_check_confidence(index, candidate, cfg))
        issues.extend(_check_review_metadata(index, candidate, cfg))

    issues.extend(_check_duplicate_conflicts(candidates))
    coverage = _build_coverage(candidates, cfg)

    return QualityReport(issues=issues, coverage=coverage)


def _check_required_fields(index: int, candidate: CanonicalCandidate) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    required = REQUIRED_NATURAL_KEYS[candidate.entity_type]

    for field in required:
        value = candidate.natural_key.get(field)
        if value is None or value == "":
            issues.append(
                QualityIssue(
                    severity="error",
                    code="missing_required_field",
                    message=f"missing required natural key field: {field}",
                    candidate_index=index,
                    field=field,
                )
            )

    if not candidate.source.snapshot_id:
        issues.append(
            QualityIssue(
                severity="error",
                code="missing_snapshot_id",
                message="candidate source is missing snapshot_id",
                candidate_index=index,
                field="source.snapshot_id",
            )
        )

    return issues


def _check_ranges(index: int, candidate: CanonicalCandidate) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    year = candidate.natural_key.get("year")
    if year is not None and not _in_range(year, 2000, 2100):
        issues.append(_range_issue(index, "year", year, "year must be between 2000 and 2100"))

    for field in SCORE_FIELDS:
        value = candidate.values.get(field)
        if value is not None and not _in_range(value, 0, 750):
            issues.append(_range_issue(index, field, value, "score must be between 0 and 750"))

    min_rank = candidate.values.get("min_rank")
    if min_rank is not None and not _in_range(min_rank, 1, 2_000_000):
        issues.append(_range_issue(index, "min_rank", min_rank, "rank must be positive"))

    plan_count = candidate.values.get("plan_count")
    if plan_count is not None and not _in_range(plan_count, 0, 10_000):
        issues.append(_range_issue(index, "plan_count", plan_count, "plan_count is out of range"))

    duration = candidate.values.get("duration")
    if duration is not None and not _in_range(duration, 2, 8):
        issues.append(_range_issue(index, "duration", duration, "duration must be 2 to 8 years"))

    tuition = candidate.values.get("tuition")
    if tuition is not None and not _in_range(tuition, 0, 200_000):
        issues.append(_range_issue(index, "tuition", tuition, "tuition is out of range"))

    return issues


def _check_freshness(
    index: int,
    candidate: CanonicalCandidate,
    config: QualityGateConfig,
) -> list[QualityIssue]:
    year = candidate.natural_key.get("year")
    if not isinstance(year, int):
        return []

    age = config.current_year - year
    if age <= config.freshness_window_years:
        return []

    return [
        QualityIssue(
            severity="warning",
            code="stale_data",
            message=f"candidate year is {age} years behind current_year",
            candidate_index=index,
            field="year",
        )
    ]


def _check_confidence(
    index: int,
    candidate: CanonicalCandidate,
    config: QualityGateConfig,
) -> list[QualityIssue]:
    if candidate.source.confidence >= config.min_agent_confidence:
        return []

    return [
        QualityIssue(
            severity="warning",
            code="low_confidence",
            message="candidate confidence is below Agent default-answer threshold",
            candidate_index=index,
            field="source.confidence",
        )
    ]


def _check_review_metadata(
    index: int,
    candidate: CanonicalCandidate,
    config: QualityGateConfig,
) -> list[QualityIssue]:
    if not config.require_review_metadata:
        return []

    issues: list[QualityIssue] = []
    review = candidate.source.review
    required_fields = {
        "source.review.reviewed_by": review.reviewed_by,
        "source.review.reviewed_at": review.reviewed_at,
    }

    for field, value in required_fields.items():
        if value is None or value == "":
            issues.append(
                QualityIssue(
                    severity="error",
                    code="missing_review_metadata",
                    message=f"candidate source is missing review metadata: {field}",
                    candidate_index=index,
                    field=field,
                )
            )

    return issues


def _check_duplicate_conflicts(candidates: list[CanonicalCandidate]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    seen: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}

    for index, candidate in enumerate(candidates):
        key = _candidate_key(candidate)
        if key not in seen:
            seen[key] = (index, candidate.values)
            continue

        first_index, first_values = seen[key]
        if first_values != candidate.values:
            issues.append(
                QualityIssue(
                    severity="error",
                    code="conflicting_duplicate",
                    message=f"candidate conflicts with earlier row at index {first_index}",
                    candidate_index=index,
                )
            )

    return issues


def _build_coverage(
    candidates: list[CanonicalCandidate],
    config: QualityGateConfig,
) -> dict[str, Any]:
    entity_counts: dict[str, int] = {}
    province_counts: dict[str, int] = {}
    year_counts: dict[str, int] = {}

    for candidate in candidates:
        entity_counts[candidate.entity_type] = entity_counts.get(candidate.entity_type, 0) + 1

        province = candidate.natural_key.get("province")
        if province:
            province_counts[str(province)] = province_counts.get(str(province), 0) + 1

        year = candidate.natural_key.get("year")
        if year:
            year_key = str(year)
            year_counts[year_key] = year_counts.get(year_key, 0) + 1

    return {
        "total": len(candidates),
        "by_entity_type": entity_counts,
        "by_province": province_counts,
        "by_year": year_counts,
        "missing_expected_provinces": [
            province for province in config.expected_provinces if province not in province_counts
        ],
        "missing_expected_years": [
            year for year in config.expected_years if str(year) not in year_counts
        ],
    }


def _candidate_key(candidate: CanonicalCandidate) -> tuple[str, str]:
    natural_key = "|".join(
        f"{key}={candidate.natural_key.get(key)}"
        for key in sorted(candidate.natural_key.keys())
    )
    return candidate.entity_type, natural_key


def _in_range(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int | float) and low <= value <= high


def _range_issue(index: int, field: str, value: Any, message: str) -> QualityIssue:
    return QualityIssue(
        severity="error",
        code="value_out_of_range",
        message=f"{message}: {value}",
        candidate_index=index,
        field=field,
    )
