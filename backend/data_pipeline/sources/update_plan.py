"""No-write source registry update planning."""

from typing import Any


ERROR = "error"


def build_source_registry_update_plan(
    registry_payload: dict[str, Any],
    approval_review: dict[str, Any],
) -> dict[str, Any]:
    """Plan source registry metadata updates from an approved review packet."""
    issues: list[dict[str, Any]] = []
    _check_approval_review(approval_review, issues)
    sources = registry_payload.get("sources")
    if not isinstance(sources, list):
        issues.append(_issue(
            "invalid_registry_sources",
            "registry.sources must be a list",
            "registry.sources",
        ))
        sources = []

    hint = _dict(approval_review.get("registry_update_hint"))
    source_id = hint.get("source_id")
    source = _find_source(sources, source_id)
    if source is None and source_id:
        issues.append(_issue(
            "source_not_found",
            f"source not found in registry: {source_id}",
            "registry.sources.source_id",
        ))

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    return {
        "action": "source_registry_update_plan",
        "passed": ready,
        "ready_for_registry_patch": ready,
        "source_id": source_id,
        "planned_updates": (
            _planned_updates(source, hint) if isinstance(source, dict) else {}
        ),
        "issue_counts": issue_counts,
        "issues": issues,
        "non_goals": _non_goals(),
    }


def _check_approval_review(
    approval_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if approval_review.get("action") != "source_review_approval_review":
        issues.append(_issue(
            "invalid_approval_review_action",
            "approval review action must be source_review_approval_review",
            "approval_review.action",
        ))
    if approval_review.get("ready_for_registry_update") is not True:
        issues.append(_issue(
            "approval_review_not_ready",
            "approval review must be ready for registry update",
            "approval_review.ready_for_registry_update",
        ))
    hint = approval_review.get("registry_update_hint")
    if not isinstance(hint, dict):
        issues.append(_issue(
            "missing_registry_update_hint",
            "approval review must include registry_update_hint",
            "approval_review.registry_update_hint",
        ))


def _find_source(sources: list[Any], source_id: Any) -> dict[str, Any] | None:
    if not isinstance(source_id, str) or not source_id:
        return None
    for source in sources:
        if isinstance(source, dict) and source.get("source_id") == source_id:
            return source
    return None


def _planned_updates(
    source: dict[str, Any],
    hint: dict[str, Any],
) -> dict[str, Any]:
    coverage = source.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    categories = _strings(source.get("data_categories"))
    provinces = _strings(coverage.get("provinces"))
    years = _ints(coverage.get("years"))
    target_status = hint.get("target_review_status")
    category = hint.get("add_data_category_if_missing")
    province = hint.get("add_province_if_missing")
    hint_years = _ints(hint.get("add_years_if_missing"))

    return {
        "review_status": {
            "current": source.get("review_status"),
            "target": target_status,
            "will_update": source.get("review_status") != target_status,
        },
        "data_categories": {
            "current": categories,
            "add": [category] if isinstance(category, str)
            and category not in categories else [],
        },
        "coverage_provinces": {
            "current": provinces,
            "add": [province] if isinstance(province, str)
            and province not in provinces else [],
        },
        "coverage_years": {
            "current": years,
            "add": [year for year in hint_years if year not in years],
        },
    }


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _ints(value: Any) -> list[int]:
    return [item for item in value if isinstance(item, int)] if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _issue(code: str, message: str, field: str) -> dict[str, str]:
    return {
        "severity": ERROR,
        "code": code,
        "message": message,
        "field": field,
    }


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {ERROR: 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _non_goals() -> list[str]:
    return [
        "Does not modify sources.json.",
        "Does not approve source review by itself.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
