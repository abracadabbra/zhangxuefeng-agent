"""Stdlib-only smoke review for parser candidate quality evidence."""

from __future__ import annotations

from typing import Any


REQUIRED_NATURAL_KEYS = {
    "admission_score": ("school_name", "province", "year", "batch", "subject_type"),
    "enrollment_plan": ("school_name", "major_name", "province", "year"),
}
SCORE_FIELDS = ("min_score", "avg_score", "max_score")


def build_quality_smoke_review(
    parser_smoke_review: dict[str, Any],
    *,
    quality_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a no-write quality smoke review from parser candidate previews."""
    cfg = _config(quality_config)
    issues: list[dict[str, Any]] = []
    candidates = _candidate_previews(parser_smoke_review, issues)

    if parser_smoke_review.get("passed") is not True:
        issues.append(_issue(
            "error",
            "parser_smoke_not_passed",
            "parser smoke review must pass before quality smoke",
            "parser_smoke_review.passed",
        ))
    if parser_smoke_review.get("ready_for_parser") is not True:
        issues.append(_issue(
            "error",
            "parser_smoke_not_ready",
            "parser smoke review must be ready before quality smoke",
            "parser_smoke_review.ready_for_parser",
        ))

    parser_scope = _object(parser_smoke_review.get("scope"))
    for index, candidate in enumerate(candidates):
        _check_required_fields(index, candidate, parser_scope, issues)
        _check_ranges(index, candidate, issues)
        _check_freshness(index, candidate, cfg, issues)
        _check_confidence(index, candidate, cfg, issues)
        _check_review_metadata(index, candidate, cfg, issues)

    _check_duplicate_conflicts(candidates, issues)
    coverage = _build_coverage(candidates, cfg)
    issue_counts = _issue_counts(issues)

    return {
        "action": "quality_smoke_review",
        "passed": issue_counts["error"] == 0,
        "ready_for_quality_gate": issue_counts["error"] == 0,
        "scope": {
            "source_id": _scope_value(parser_smoke_review, "source_id"),
            "snapshot_id": _scope_value(parser_smoke_review, "snapshot_id"),
            "dataset": _scope_value(parser_smoke_review, "dataset"),
            "candidate_count": len(candidates),
        },
        "source_metadata": _source_metadata(candidates),
        "coverage": coverage,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues, coverage),
        "non_goals": [
            "Does not execute the pydantic quality gate.",
            "Does not modify parser output.",
            "Does not write database rows or seed data.",
            "Does not approve loader execution.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _candidate_previews(
    parser_smoke_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = parser_smoke_review.get("candidate_previews")
    if not isinstance(candidates, list):
        issues.append(_issue(
            "error",
            "invalid_candidate_previews",
            "parser smoke candidate_previews must be a list",
            "parser_smoke_review.candidate_previews",
        ))
        return []
    normalized = []
    for index, candidate in enumerate(candidates):
        if isinstance(candidate, dict):
            normalized.append(candidate)
        else:
            issues.append(_issue(
                "error",
                "invalid_candidate_preview",
                "each parser smoke candidate preview must be an object",
                f"candidate_previews[{index}]",
            ))
    if not candidates:
        issues.append(_issue(
            "error",
            "empty_candidate_previews",
            "candidate_previews must not be empty",
            "parser_smoke_review.candidate_previews",
        ))
    return normalized


def _check_required_fields(
    index: int,
    candidate: dict[str, Any],
    parser_scope: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    entity_type = candidate.get("entity_type")
    natural_key = _object(candidate.get("natural_key"))
    if entity_type not in REQUIRED_NATURAL_KEYS:
        issues.append(_issue(
            "error",
            "unsupported_entity_type",
            f"unsupported entity_type: {entity_type}",
            f"candidate_previews[{index}].entity_type",
        ))
        return
    for field in REQUIRED_NATURAL_KEYS[entity_type]:
        value = natural_key.get(field)
        if value is None or value == "":
            issues.append(_issue(
                "error",
                "missing_required_field",
                f"missing required natural key field: {field}",
                f"candidate_previews[{index}].natural_key.{field}",
            ))
    source = _object(candidate.get("source"))
    if not source.get("source_id"):
        issues.append(_issue(
            "error",
            "missing_source_id",
            "candidate source is missing source_id",
            f"candidate_previews[{index}].source.source_id",
        ))
    if not source.get("snapshot_id"):
        issues.append(_issue(
            "error",
            "missing_snapshot_id",
            "candidate source is missing snapshot_id",
            f"candidate_previews[{index}].source.snapshot_id",
        ))
    if not source.get("dataset"):
        issues.append(_issue(
            "error",
            "missing_source_dataset",
            "candidate source is missing dataset",
            f"candidate_previews[{index}].source.dataset",
        ))
    if not isinstance(source.get("year"), int):
        issues.append(_issue(
            "error",
            "missing_source_year",
            "candidate source is missing year",
            f"candidate_previews[{index}].source.year",
        ))
    _check_source_metadata_matches(index, source, natural_key, parser_scope, issues)


def _check_source_metadata_matches(
    index: int,
    source: dict[str, Any],
    natural_key: dict[str, Any],
    parser_scope: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    checks = (
        ("source_id", parser_scope.get("source_id")),
        ("snapshot_id", parser_scope.get("snapshot_id")),
        ("dataset", parser_scope.get("dataset")),
    )
    for field, expected in checks:
        actual = source.get(field)
        if expected and actual and actual != expected:
            issues.append(_issue(
                "error",
                f"unexpected_source_{field}",
                f"candidate source {field} does not match parser scope",
                f"candidate_previews[{index}].source.{field}",
            ))
    source_year = source.get("year")
    natural_key_year = natural_key.get("year")
    if (
        isinstance(source_year, int)
        and isinstance(natural_key_year, int)
        and source_year != natural_key_year
    ):
        issues.append(_issue(
            "error",
            "unexpected_source_year",
            "candidate source year does not match natural key year",
            f"candidate_previews[{index}].source.year",
        ))


def _check_ranges(
    index: int,
    candidate: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    natural_key = _object(candidate.get("natural_key"))
    values = _object(candidate.get("values"))
    year = natural_key.get("year")
    if year is not None and not _in_range(year, 2000, 2100):
        _range_issue(index, "year", year, "year must be between 2000 and 2100", issues)
    for field in SCORE_FIELDS:
        value = values.get(field)
        if value is not None and not _in_range(value, 0, 750):
            _range_issue(index, field, value, "score must be between 0 and 750", issues)
    min_rank = values.get("min_rank")
    if min_rank is not None and not _in_range(min_rank, 1, 2_000_000):
        _range_issue(index, "min_rank", min_rank, "rank must be positive", issues)
    plan_count = values.get("plan_count")
    if plan_count is not None and not _in_range(plan_count, 0, 10_000):
        _range_issue(index, "plan_count", plan_count, "plan_count is out of range", issues)
    duration = values.get("duration")
    if duration is not None and not _in_range(duration, 2, 8):
        _range_issue(index, "duration", duration, "duration must be 2 to 8 years", issues)
    tuition = values.get("tuition")
    if tuition is not None and not _in_range(tuition, 0, 200_000):
        _range_issue(index, "tuition", tuition, "tuition is out of range", issues)


def _check_freshness(
    index: int,
    candidate: dict[str, Any],
    cfg: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    year = _object(candidate.get("natural_key")).get("year")
    if not isinstance(year, int):
        return
    age = cfg["current_year"] - year
    if age > cfg["freshness_window_years"]:
        issues.append(_issue(
            "warning",
            "stale_data",
            f"candidate year is {age} years behind current_year",
            f"candidate_previews[{index}].natural_key.year",
        ))


def _check_confidence(
    index: int,
    candidate: dict[str, Any],
    cfg: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    confidence = _object(candidate.get("source")).get("confidence", 0)
    if isinstance(confidence, int | float) and confidence >= cfg["min_agent_confidence"]:
        return
    issues.append(_issue(
        "warning",
        "low_confidence",
        "candidate confidence is below Agent default-answer threshold",
        f"candidate_previews[{index}].source.confidence",
    ))


def _check_review_metadata(
    index: int,
    candidate: dict[str, Any],
    cfg: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if not cfg["require_review_metadata"]:
        return
    if _object(candidate.get("source")).get("has_review_metadata") is True:
        return
    issues.append(_issue(
        "error",
        "missing_review_metadata",
        "candidate source is missing review metadata",
        f"candidate_previews[{index}].source.has_review_metadata",
    ))


def _check_duplicate_conflicts(
    candidates: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    seen: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
    for index, candidate in enumerate(candidates):
        key = _candidate_key(candidate)
        values = _object(candidate.get("values"))
        if key not in seen:
            seen[key] = (index, values)
            continue
        first_index, first_values = seen[key]
        if values != first_values:
            issues.append(_issue(
                "error",
                "conflicting_duplicate",
                f"candidate conflicts with earlier row at index {first_index}",
                f"candidate_previews[{index}]",
            ))


def _build_coverage(
    candidates: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    entity_counts: dict[str, int] = {}
    province_counts: dict[str, int] = {}
    year_counts: dict[str, int] = {}
    for candidate in candidates:
        entity_type = candidate.get("entity_type")
        if entity_type:
            entity_counts[str(entity_type)] = entity_counts.get(str(entity_type), 0) + 1
        natural_key = _object(candidate.get("natural_key"))
        province = natural_key.get("province")
        if province:
            province_counts[str(province)] = province_counts.get(str(province), 0) + 1
        year = natural_key.get("year")
        if year:
            year_counts[str(year)] = year_counts.get(str(year), 0) + 1
    return {
        "total": len(candidates),
        "by_entity_type": entity_counts,
        "by_province": province_counts,
        "by_year": year_counts,
        "missing_expected_provinces": [
            province for province in cfg["expected_provinces"]
            if province not in province_counts
        ],
        "missing_expected_years": [
            year for year in cfg["expected_years"]
            if str(year) not in year_counts
        ],
    }


def _source_metadata(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    source_ids: list[str] = []
    snapshot_ids: list[str] = []
    datasets: list[str] = []
    years: list[int] = []
    confidences: list[float] = []
    missing_source_ids = 0
    missing_snapshot_ids = 0

    for candidate in candidates:
        source = _object(candidate.get("source"))
        source_id = source.get("source_id")
        snapshot_id = source.get("snapshot_id")
        dataset = source.get("dataset")
        year = source.get("year")
        confidence = source.get("confidence")
        if isinstance(source_id, str) and source_id:
            source_ids.append(source_id)
        else:
            missing_source_ids += 1
        if isinstance(snapshot_id, str) and snapshot_id:
            snapshot_ids.append(snapshot_id)
        else:
            missing_snapshot_ids += 1
        if isinstance(dataset, str) and dataset:
            datasets.append(dataset)
        if isinstance(year, int):
            years.append(year)
        if isinstance(confidence, int | float):
            confidences.append(float(confidence))

    return {
        "source_ids": _unique(source_ids),
        "snapshot_ids": _unique(snapshot_ids),
        "datasets": _unique(datasets),
        "years": _unique(years),
        "confidence_min": min(confidences) if confidences else None,
        "confidence_max": max(confidences) if confidences else None,
        "missing_source_ids": missing_source_ids,
        "missing_snapshot_ids": missing_snapshot_ids,
    }


def _unique(values: list[Any]) -> list[Any]:
    unique_values: list[Any] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def _required_reviews(
    issues: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> list[str]:
    reviews: list[str] = []
    codes = {issue["code"] for issue in issues}
    if "missing_required_field" in codes:
        reviews.append("Fill required quality natural-key fields.")
    if "value_out_of_range" in codes:
        reviews.append("Resolve out-of-range quality values.")
    if "conflicting_duplicate" in codes:
        reviews.append("Resolve conflicting duplicate candidate rows.")
    if "missing_review_metadata" in codes:
        reviews.append("Fill row review metadata before quality gate.")
    source_metadata_codes = {
        "missing_source_id",
        "missing_snapshot_id",
        "missing_source_dataset",
        "missing_source_year",
    }
    if codes & source_metadata_codes:
        reviews.append("Fill candidate source metadata before quality gate.")
    source_metadata_mismatch_codes = {
        "unexpected_source_source_id",
        "unexpected_source_snapshot_id",
        "unexpected_source_dataset",
        "unexpected_source_year",
    }
    if codes & source_metadata_mismatch_codes:
        reviews.append("Align candidate source metadata before quality gate.")
    if coverage.get("missing_expected_provinces") or coverage.get("missing_expected_years"):
        reviews.append("Review expected coverage before loader discussion.")
    return reviews


def _config(quality_config: dict[str, Any] | None) -> dict[str, Any]:
    payload = quality_config or {}
    return {
        "current_year": _int_value(payload.get("current_year"), 2026),
        "freshness_window_years": _int_value(
            payload.get("freshness_window_years"),
            1,
        ),
        "min_agent_confidence": _float_value(
            payload.get("min_agent_confidence"),
            0.8,
        ),
        "expected_provinces": tuple(_list_value(payload.get("expected_provinces"))),
        "expected_years": tuple(_list_value(payload.get("expected_years"))),
        "require_review_metadata": bool(payload.get("require_review_metadata")),
    }


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, str]:
    natural_key = _object(candidate.get("natural_key"))
    natural_key_text = "|".join(
        f"{key}={natural_key.get(key)}"
        for key in sorted(natural_key)
    )
    return str(candidate.get("entity_type")), natural_key_text


def _scope_value(parser_smoke_review: dict[str, Any], field: str) -> Any:
    return _object(parser_smoke_review.get("scope")).get(field)


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_value(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _float_value(value: Any, default: float) -> float:
    return float(value) if isinstance(value, int | float) else default


def _in_range(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int | float) and low <= value <= high


def _range_issue(
    index: int,
    field: str,
    value: Any,
    message: str,
    issues: list[dict[str, Any]],
) -> None:
    issues.append(_issue(
        "error",
        "value_out_of_range",
        f"{message}: {value}",
        f"candidate_previews[{index}].{field}",
    ))


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _issue(
    severity: str,
    code: str,
    message: str,
    field: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "field": field,
    }
