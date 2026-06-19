"""Stdlib-only source registry scope audit fallback."""

from typing import Any

from backend.data_pipeline.sources.smoke import build_source_registry_smoke_review


def build_source_scope_smoke_audit(
    payload: dict[str, Any],
    *,
    data_category: str,
    expected_provinces: list[str] | tuple[str, ...] = (),
    expected_years: list[int] | tuple[int, ...] = (),
    require_reviewed: bool = False,
) -> dict[str, Any]:
    """Build a source-audit-shaped scope review without pydantic imports."""
    issues = _structural_issues(payload)
    sources = payload.get("sources")
    sources = sources if isinstance(sources, list) else []
    category_sources = [
        source for source in sources
        if isinstance(source, dict) and _has_category(source, data_category)
    ]
    if not category_sources:
        issues.append(_issue(
            "error",
            "missing_category_source",
            f"no source covers data category: {data_category}",
        ))
    else:
        for province in expected_provinces:
            matching_sources = [
                source for source in category_sources
                if _covers_province(source, province)
            ]
            if not matching_sources:
                issues.append(_issue(
                    "error",
                    "missing_province_source",
                    f"no {data_category} source covers province: {province}",
                ))
                continue
            issues.extend(_review_issues_for_sources(
                matching_sources,
                expected_years=expected_years,
                require_reviewed=require_reviewed,
            ))

    return {
        "scope": {
            "data_category": data_category,
            "expected_provinces": list(expected_provinces),
            "expected_years": list(expected_years),
            "require_reviewed": require_reviewed,
        },
        "passed": not any(issue["severity"] == "error" for issue in issues),
        "issues": issues,
    }


def _structural_issues(payload: dict[str, Any]) -> list[dict[str, Any]]:
    review = build_source_registry_smoke_review(payload)
    issues = []
    for issue in review["issues"]:
        if issue["severity"] == "error":
            issues.append(_issue(
                "error",
                f"registry_{issue['code']}",
                issue["message"],
            ))
    return issues


def _has_category(source: dict[str, Any], data_category: str) -> bool:
    categories = source.get("data_categories")
    return isinstance(categories, list) and data_category in categories


def _covers_province(source: dict[str, Any], province: str) -> bool:
    coverage = source.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    provinces = coverage.get("provinces")
    if not isinstance(provinces, list):
        return False
    return "全国" in provinces or province in provinces


def _review_issues_for_sources(
    sources: list[dict[str, Any]],
    *,
    expected_years: list[int] | tuple[int, ...],
    require_reviewed: bool,
) -> list[dict[str, Any]]:
    issues = []
    for source in sources:
        source_id = source.get("source_id")
        source_id = source_id if isinstance(source_id, str) else None
        review_status = source.get("review_status")
        if require_reviewed and review_status not in ("reviewed", "approved"):
            issues.append(_issue(
                "warning",
                "source_not_reviewed",
                f"source is not reviewed or approved: {source_id}",
                source_id=source_id,
            ))
        coverage = source.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        years = coverage.get("years")
        years = years if isinstance(years, list) else []
        if expected_years and not years:
            issues.append(_issue(
                "warning",
                "source_years_not_registered",
                f"source has no registered coverage years: {source_id}",
                source_id=source_id,
            ))
            continue
        missing_years = [
            year for year in expected_years if year not in years
        ]
        for year in missing_years:
            issues.append(_issue(
                "warning",
                "source_year_not_registered",
                f"source does not register coverage for year {year}",
                source_id=source_id,
            ))
    return issues


def _issue(
    severity: str,
    code: str,
    message: str,
    *,
    source_id: str | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "source_id": source_id,
    }
