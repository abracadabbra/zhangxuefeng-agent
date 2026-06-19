"""Aggregate smoke for source registry patch approval and preview."""

from typing import Any

from backend.data_pipeline.sources.patch_preview import (
    build_source_registry_patch_preview,
)


def build_source_registry_patch_chain_smoke(
    *,
    registry_payload: dict[str, Any],
    update_plan: dict[str, Any],
    patch_approval_review: dict[str, Any],
) -> dict[str, Any]:
    """Check the no-write chain before any source registry patch is executed."""
    patch_preview = build_source_registry_patch_preview(
        registry_payload,
        update_plan,
        patch_approval_review,
    )
    checks = {
        "patch_approval_ready": (
            patch_approval_review.get("ready_for_registry_patch_execution")
            is True
        ),
        "patch_preview_ready": (
            patch_preview.get("ready_for_registry_patch_preview") is True
        ),
        "registry_not_modified": True,
    }
    issues = _aggregate_issues(patch_approval_review, patch_preview)
    issue_counts = _issue_counts(issues)
    return {
        "action": "source_registry_patch_chain_smoke",
        "passed": all(checks.values()) and issue_counts["error"] == 0,
        "source_id": update_plan.get("source_id")
        or patch_approval_review.get("source_id"),
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(
            patch_approval_review,
            patch_preview,
        ),
        "reviews": {
            "patch_approval_review": patch_approval_review,
            "patch_preview": patch_preview,
        },
        "non_goals": _non_goals(),
    }


def _aggregate_issues(
    patch_approval_review: dict[str, Any],
    patch_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = []
    if patch_approval_review.get("ready_for_registry_patch_execution") is not True:
        issues.append(_issue(
            "error",
            "patch_approval_review_not_ready",
            "source registry patch approval review must pass",
            "patch_approval_review.ready_for_registry_patch_execution",
        ))
    if patch_preview.get("ready_for_registry_patch_preview") is not True:
        issues.append(_issue(
            "error",
            "patch_preview_not_ready",
            "source registry patch preview must pass",
            "patch_preview.ready_for_registry_patch_preview",
        ))
    return issues


def _required_reviews(
    patch_approval_review: dict[str, Any],
    patch_preview: dict[str, Any],
) -> list[str]:
    reviews = []
    reviews.extend(_strings(patch_approval_review.get("required_reviews")))
    reviews.extend(_strings(patch_preview.get("required_reviews")))
    if patch_approval_review.get("ready_for_registry_patch_execution") is not True:
        reviews.append("Pass source registry patch approval review.")
    if patch_preview.get("ready_for_registry_patch_preview") is not True:
        reviews.append("Resolve source registry patch preview blockers.")
    return _unique(reviews)


def _issue(severity: str, code: str, message: str, field: str) -> dict[str, str]:
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


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _non_goals() -> list[str]:
    return [
        "Does not modify sources.json.",
        "Does not approve source review by itself.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
