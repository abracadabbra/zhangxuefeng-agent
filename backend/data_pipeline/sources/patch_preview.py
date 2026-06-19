"""No-write source registry patch preview helpers."""

from copy import deepcopy
from typing import Any


ERROR = "error"


def build_source_registry_patch_preview(
    registry_payload: dict[str, Any],
    update_plan: dict[str, Any],
    patch_approval_review: dict[str, Any],
) -> dict[str, Any]:
    """Preview a source registry patch without modifying the registry file."""
    issues: list[dict[str, Any]] = []
    _check_update_plan(update_plan, issues)
    _check_patch_approval_review(patch_approval_review, update_plan, issues)
    sources = registry_payload.get("sources")
    if not isinstance(sources, list):
        _issue(
            issues,
            "invalid_registry_sources",
            "registry.sources must be a list",
            "registry.sources",
        )
        sources = []

    source_id = update_plan.get("source_id")
    source = _find_source(sources, source_id)
    if source is None and isinstance(source_id, str) and source_id:
        _issue(
            issues,
            "source_not_found",
            f"source not found in registry: {source_id}",
            "registry.sources.source_id",
        )

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    patched_source, changes = (
        _patched_source(source, update_plan) if ready and source else ({}, [])
    )
    return {
        "action": "source_registry_patch_preview",
        "passed": ready,
        "ready_for_registry_patch_preview": ready,
        "source_id": source_id,
        "changes_applied": changes,
        "patched_source": patched_source,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "non_goals": _non_goals(),
    }


def _check_update_plan(
    update_plan: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if update_plan.get("action") != "source_registry_update_plan":
        _issue(
            issues,
            "invalid_update_plan_action",
            "update plan action must be source_registry_update_plan",
            "update_plan.action",
        )
    if update_plan.get("ready_for_registry_patch") is not True:
        _issue(
            issues,
            "update_plan_not_ready",
            "update plan must be ready for registry patch",
            "update_plan.ready_for_registry_patch",
        )
    if not isinstance(update_plan.get("planned_updates"), dict):
        _issue(
            issues,
            "missing_planned_updates",
            "update plan must include planned_updates",
            "update_plan.planned_updates",
        )


def _check_patch_approval_review(
    approval_review: dict[str, Any],
    update_plan: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if approval_review.get("action") != "source_registry_patch_approval_review":
        _issue(
            issues,
            "invalid_patch_approval_review_action",
            "approval review action must be source_registry_patch_approval_review",
            "patch_approval_review.action",
        )
    if approval_review.get("ready_for_registry_patch_execution") is not True:
        _issue(
            issues,
            "patch_approval_review_not_ready",
            "patch approval review must be ready for registry patch execution",
            "patch_approval_review.ready_for_registry_patch_execution",
        )
    if approval_review.get("source_id") != update_plan.get("source_id"):
        _issue(
            issues,
            "source_id_mismatch",
            "patch approval review source_id must match update plan source_id",
            "patch_approval_review.source_id",
        )


def _patched_source(
    source: dict[str, Any],
    update_plan: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    patched = deepcopy(source)
    changes = []
    planned_updates = _dict(update_plan.get("planned_updates"))

    review_status = _dict(planned_updates.get("review_status"))
    target_status = review_status.get("target")
    if isinstance(target_status, str):
        patched["review_status"] = target_status
        changes.append("review_status")

    categories = _list(patched.get("data_categories"))
    category_updates = _dict(planned_updates.get("data_categories"))
    patched["data_categories"] = _append_unique(
        categories,
        _strings(category_updates.get("add")),
    )
    if patched["data_categories"] != categories:
        changes.append("data_categories")

    coverage = deepcopy(_dict(patched.get("coverage")))
    provinces = _list(coverage.get("provinces"))
    province_updates = _dict(planned_updates.get("coverage_provinces"))
    coverage["provinces"] = _append_unique(
        provinces,
        _strings(province_updates.get("add")),
    )
    if coverage["provinces"] != provinces:
        changes.append("coverage.provinces")

    years = _list(coverage.get("years"))
    year_updates = _dict(planned_updates.get("coverage_years"))
    coverage["years"] = _append_unique(years, _ints(year_updates.get("add")))
    if coverage["years"] != years:
        changes.append("coverage.years")
    patched["coverage"] = coverage

    return patched, changes


def _append_unique(values: list[Any], additions: list[Any]) -> list[Any]:
    result = list(values)
    for item in additions:
        if item not in result:
            result.append(item)
    return result


def _find_source(sources: list[Any], source_id: Any) -> dict[str, Any] | None:
    if not isinstance(source_id, str) or not source_id:
        return None
    for source in sources:
        if isinstance(source, dict) and source.get("source_id") == source_id:
            return source
    return None


def _issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    field: str,
) -> None:
    issues.append({
        "severity": ERROR,
        "code": code,
        "message": message,
        "field": field,
    })


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {ERROR: 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _required_reviews(issues: list[dict[str, Any]]) -> list[str]:
    reviews = []
    for issue in issues:
        review = _required_review_for_issue(str(issue.get("code") or ""))
        if review and review not in reviews:
            reviews.append(review)
    return reviews


def _required_review_for_issue(code: str) -> str | None:
    reviews = {
        "invalid_registry_sources": "Provide a valid source registry.",
        "source_not_found": "Register the source before previewing the patch.",
        "invalid_update_plan_action": (
            "Provide a source_registry_update_plan artifact."
        ),
        "update_plan_not_ready": "Resolve source registry update plan blockers.",
        "missing_planned_updates": "Provide planned registry updates.",
        "invalid_patch_approval_review_action": (
            "Provide a source_registry_patch_approval_review artifact."
        ),
        "patch_approval_review_not_ready": (
            "Pass source registry patch approval review."
        ),
        "source_id_mismatch": "Align source id across registry patch artifacts.",
    }
    return reviews.get(code)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _ints(value: Any) -> list[int]:
    return [item for item in value if isinstance(item, int)] if isinstance(value, list) else []


def _non_goals() -> list[str]:
    return [
        "Does not modify sources.json.",
        "Does not approve source review by itself.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
