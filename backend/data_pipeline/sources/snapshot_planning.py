"""No-write source readiness review before raw snapshot preparation."""

from typing import Any

from backend.data_pipeline.sources.scope_smoke import build_source_scope_smoke_audit


def build_source_snapshot_planning_review(
    registry_payload: dict[str, Any],
    *,
    data_category: str,
    province: str,
    year: int,
) -> dict[str, Any]:
    """Review whether a scoped source is ready for raw snapshot preparation."""
    source_scope_audit = build_source_scope_smoke_audit(
        registry_payload,
        data_category=data_category,
        expected_provinces=[province],
        expected_years=[year],
        require_reviewed=True,
    )
    blockers = _blockers(source_scope_audit)
    ready = not blockers
    return {
        "action": "source_snapshot_planning_review",
        "passed": ready,
        "ready_for_snapshot_planning": ready,
        "scope": {
            "data_category": data_category,
            "province": province,
            "year": year,
        },
        "blockers": blockers,
        "required_reviews": _required_reviews(blockers),
        "source_summary": _source_summary(
            registry_payload,
            data_category=data_category,
            province=province,
            year=year,
        ),
        "source_scope_audit": source_scope_audit,
        "non_goals": _non_goals(),
    }


def _blockers(source_scope_audit: dict[str, Any]) -> list[str]:
    blockers = []
    for issue in _dicts(source_scope_audit.get("issues")):
        severity = issue.get("severity")
        code = issue.get("code")
        if severity in ("error", "warning") and isinstance(code, str):
            blockers.append(f"source_scope:{code}")
    return blockers


def _required_reviews(blockers: list[str]) -> list[str]:
    reviews = []
    for blocker in blockers:
        review = _required_review_for_blocker(blocker)
        if review and review not in reviews:
            reviews.append(review)
    return reviews


def _required_review_for_blocker(blocker: str) -> str | None:
    reviews = {
        "source_scope:registry_invalid_registry_sources": (
            "Provide a valid source registry."
        ),
        "source_scope:missing_category_source": (
            "Register a source for the requested data category."
        ),
        "source_scope:missing_province_source": (
            "Register a source for the requested province."
        ),
        "source_scope:source_not_reviewed": (
            "Approve or review the source before preparing a raw snapshot."
        ),
        "source_scope:source_years_not_registered": (
            "Register reviewed source coverage years before snapshot planning."
        ),
        "source_scope:source_year_not_registered": (
            "Register the requested source coverage year before snapshot planning."
        ),
    }
    return reviews.get(blocker)


def _source_summary(
    registry_payload: dict[str, Any],
    *,
    data_category: str,
    province: str,
    year: int,
) -> dict[str, Any]:
    matching_sources = [
        source for source in _dicts(registry_payload.get("sources"))
        if _has_category(source, data_category)
        and _covers_province(source, province)
    ]
    review_statuses = _sorted_strings(
        source.get("review_status") for source in matching_sources
    )
    coverage_years = _sorted_ints(
        year
        for source in matching_sources
        for year in _coverage_years(source)
    )
    return {
        "matching_source_ids": _sorted_strings(
            source.get("source_id") for source in matching_sources
        ),
        "review_statuses": review_statuses,
        "coverage_years": coverage_years,
        "has_matching_source": bool(matching_sources),
        "has_approved_source": "approved" in review_statuses,
        "has_requested_year": year in coverage_years,
    }


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


def _coverage_years(source: dict[str, Any]) -> list[int]:
    coverage = source.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    years = coverage.get("years")
    return [year for year in years if isinstance(year, int)] if isinstance(years, list) else []


def _sorted_strings(values: Any) -> list[str]:
    return sorted(value for value in values if isinstance(value, str))


def _sorted_ints(values: Any) -> list[int]:
    return sorted({value for value in values if isinstance(value, int)})


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _non_goals() -> list[str]:
    return [
        "Does not modify sources.json.",
        "Does not approve source review by itself.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not parse rows or run quality gates.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
