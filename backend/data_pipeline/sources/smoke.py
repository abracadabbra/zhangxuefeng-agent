"""Stdlib-only source registry smoke review."""

from typing import Any


REQUIRED_SOURCE_FIELDS = (
    "source_id",
    "name",
    "source_type",
    "homepage_url",
    "data_categories",
    "coverage",
    "trust_score",
    "update_frequency",
    "collection_method",
    "license_note",
    "review_status",
)
ALLOWED_REVIEW_STATUSES = {"candidate", "reviewed", "approved", "rejected"}
ALLOWED_SOURCE_ID_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def build_source_registry_smoke_review(
    payload: dict[str, Any],
    *,
    expected_source_ids: list[str] | tuple[str, ...] = (),
    expected_provinces: list[str] | tuple[str, ...] = (),
    expected_data_categories: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build a no-dependency structural review for source registry JSON."""
    issues: list[dict[str, Any]] = []
    sources = payload.get("sources")
    if not isinstance(sources, list):
        issues.append(_issue(
            "error",
            "invalid_sources_list",
            "registry.sources must be a list",
            "sources",
        ))
        sources = []

    seen_source_ids: dict[str, int] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            issues.append(_issue(
                "error",
                "invalid_source_entry",
                "source entry must be an object",
                f"sources[{index}]",
            ))
            continue
        _review_source(index, source, seen_source_ids, issues)

    coverage_summary = _coverage_summary(sources)
    issues.extend(_expectation_issues(
        coverage_summary,
        expected_source_ids=expected_source_ids,
        expected_provinces=expected_provinces,
        expected_data_categories=expected_data_categories,
    ))

    issue_counts = _issue_counts(issues)
    return {
        "action": "source_registry_smoke_review",
        "passed": issue_counts["error"] == 0,
        "source_count": len(sources),
        "issue_counts": issue_counts,
        "issues": issues,
        "coverage_summary": coverage_summary,
        "non_goals": _non_goals(),
    }


def _review_source(
    index: int,
    source: dict[str, Any],
    seen_source_ids: dict[str, int],
    issues: list[dict[str, Any]],
) -> None:
    field_prefix = f"sources[{index}]"
    for field in REQUIRED_SOURCE_FIELDS:
        if field not in source:
            issues.append(_issue(
                "error",
                f"missing_source_{field}",
                f"source is missing required field: {field}",
                f"{field_prefix}.{field}",
            ))

    source_id = source.get("source_id")
    if isinstance(source_id, str) and source_id:
        if any(char not in ALLOWED_SOURCE_ID_CHARS for char in source_id):
            issues.append(_issue(
                "error",
                "invalid_source_id",
                "source_id must contain only letters, numbers, hyphen, or underscore",
                f"{field_prefix}.source_id",
            ))
        if source_id in seen_source_ids:
            issues.append(_issue(
                "error",
                "duplicate_source_id",
                f"duplicate source_id: {source_id}",
                f"{field_prefix}.source_id",
            ))
        seen_source_ids[source_id] = index
    else:
        issues.append(_issue(
            "error",
            "invalid_source_id",
            "source_id must be a non-empty string",
            f"{field_prefix}.source_id",
        ))

    _review_homepage_url(field_prefix, source, issues)
    _review_data_categories(field_prefix, source, issues)
    _review_coverage(field_prefix, source, issues)
    _review_trust_score(field_prefix, source, issues)
    _review_review_status(field_prefix, source, issues)


def _review_homepage_url(
    field_prefix: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    homepage_url = source.get("homepage_url")
    if not isinstance(homepage_url, str) or not homepage_url.startswith(("http://", "https://")):
        issues.append(_issue(
            "error",
            "invalid_homepage_url",
            "homepage_url must be an http(s) URL string",
            f"{field_prefix}.homepage_url",
        ))


def _review_data_categories(
    field_prefix: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    categories = source.get("data_categories")
    if not isinstance(categories, list) or not categories:
        issues.append(_issue(
            "error",
            "invalid_data_categories",
            "data_categories must be a non-empty list",
            f"{field_prefix}.data_categories",
        ))
        return
    if not all(isinstance(category, str) and category for category in categories):
        issues.append(_issue(
            "error",
            "invalid_data_category",
            "data_categories values must be non-empty strings",
            f"{field_prefix}.data_categories",
        ))


def _review_coverage(
    field_prefix: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    coverage = source.get("coverage")
    if not isinstance(coverage, dict):
        issues.append(_issue(
            "error",
            "invalid_coverage",
            "coverage must be an object",
            f"{field_prefix}.coverage",
        ))
        return

    provinces = coverage.get("provinces")
    years = coverage.get("years")
    if not isinstance(provinces, list):
        issues.append(_issue(
            "error",
            "invalid_coverage_provinces",
            "coverage.provinces must be a list",
            f"{field_prefix}.coverage.provinces",
        ))
    elif not all(isinstance(province, str) and province for province in provinces):
        issues.append(_issue(
            "error",
            "invalid_coverage_province",
            "coverage.provinces values must be non-empty strings",
            f"{field_prefix}.coverage.provinces",
        ))

    if not isinstance(years, list):
        issues.append(_issue(
            "error",
            "invalid_coverage_years",
            "coverage.years must be a list",
            f"{field_prefix}.coverage.years",
        ))
        return
    invalid_years = [
        year for year in years if not isinstance(year, int) or year < 2000 or year > 2100
    ]
    if invalid_years:
        issues.append(_issue(
            "error",
            "invalid_coverage_year",
            f"coverage.years contains invalid years: {invalid_years}",
            f"{field_prefix}.coverage.years",
        ))


def _review_trust_score(
    field_prefix: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    trust_score = source.get("trust_score")
    if not isinstance(trust_score, int | float) or trust_score < 0 or trust_score > 1:
        issues.append(_issue(
            "error",
            "invalid_trust_score",
            "trust_score must be a number between 0 and 1",
            f"{field_prefix}.trust_score",
        ))


def _review_review_status(
    field_prefix: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    review_status = source.get("review_status")
    if review_status not in ALLOWED_REVIEW_STATUSES:
        issues.append(_issue(
            "error",
            "invalid_review_status",
            "review_status is invalid",
            f"{field_prefix}.review_status",
        ))


def _coverage_summary(sources: list[Any]) -> dict[str, Any]:
    provinces = set()
    categories = set()
    source_ids = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if isinstance(source_id, str):
            source_ids.append(source_id)
        for category in source.get("data_categories") or []:
            if isinstance(category, str):
                categories.add(category)
        coverage = source.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        for province in coverage.get("provinces") or []:
            if isinstance(province, str):
                provinces.add(province)
    return {
        "source_ids": sorted(source_ids),
        "provinces": sorted(provinces),
        "data_categories": sorted(categories),
    }


def _expectation_issues(
    coverage_summary: dict[str, Any],
    *,
    expected_source_ids: list[str] | tuple[str, ...],
    expected_provinces: list[str] | tuple[str, ...],
    expected_data_categories: list[str] | tuple[str, ...],
) -> list[dict[str, Any]]:
    issues = []
    issues.extend(_missing_expected_values(
        actual=coverage_summary["source_ids"],
        expected=expected_source_ids,
        code="missing_expected_source_id",
        field="coverage_summary.source_ids",
        label="source_id",
    ))
    issues.extend(_missing_expected_values(
        actual=coverage_summary["provinces"],
        expected=expected_provinces,
        code="missing_expected_province",
        field="coverage_summary.provinces",
        label="province",
    ))
    issues.extend(_missing_expected_values(
        actual=coverage_summary["data_categories"],
        expected=expected_data_categories,
        code="missing_expected_data_category",
        field="coverage_summary.data_categories",
        label="data_category",
    ))
    return issues


def _missing_expected_values(
    *,
    actual: list[str],
    expected: list[str] | tuple[str, ...],
    code: str,
    field: str,
    label: str,
) -> list[dict[str, str]]:
    actual_values = set(actual)
    issues = []
    for value in expected:
        if value not in actual_values:
            issues.append(_issue(
                "error",
                code,
                f"expected {label} is missing: {value}",
                field,
            ))
    return issues


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


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _non_goals() -> list[str]:
    return [
        "Does not replace the pydantic source registry contract.",
        "Does not perform scope audit for a pilot.",
        "Does not fetch remote source pages.",
        "Does not approve source review status or dataset years.",
    ]
