"""Aggregate smoke for source review approval and registry update planning."""

from typing import Any

from backend.data_pipeline.sources.review_approval import review_source_approval
from backend.data_pipeline.sources.scope_smoke import build_source_scope_smoke_audit
from backend.data_pipeline.sources.update_plan import (
    build_source_registry_update_plan,
)


def build_source_review_chain_smoke(
    *,
    registry_payload: dict[str, Any],
    approval_payload: dict[str, Any],
) -> dict[str, Any]:
    """Check the no-write chain from source warning to registry update plan."""
    approval_scope = _dict(approval_payload.get("scope"))
    source_scope_audit = build_source_scope_smoke_audit(
        registry_payload,
        data_category=str(approval_scope.get("data_category") or ""),
        expected_provinces=_single_value_list(approval_scope.get("province")),
        expected_years=_ints(approval_scope.get("years")),
        require_reviewed=True,
    )
    approval_review = review_source_approval(approval_payload)
    update_plan = build_source_registry_update_plan(
        registry_payload,
        approval_review,
    )
    checks = {
        "source_scope_audit_passed": source_scope_audit.get("passed") is True,
        "approval_review_passed": approval_review.get("passed") is True,
        "update_plan_ready": update_plan.get("ready_for_registry_patch") is True,
        "registry_not_modified": True,
    }
    issues = _aggregate_issues(source_scope_audit, approval_review, update_plan)
    issue_counts = _issue_counts(issues)
    return {
        "action": "source_review_chain_smoke",
        "passed": all(checks.values()) and issue_counts["error"] == 0,
        "scope": {
            "source_id": approval_payload.get("source_id"),
            "data_category": approval_scope.get("data_category"),
            "province": approval_scope.get("province"),
            "years": _ints(approval_scope.get("years")),
        },
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(
            source_scope_audit,
            approval_review,
            update_plan,
        ),
        "reviews": {
            "source_scope_audit": source_scope_audit,
            "approval_review": approval_review,
            "update_plan": update_plan,
        },
        "non_goals": _non_goals(),
    }


def _aggregate_issues(
    source_scope_audit: dict[str, Any],
    approval_review: dict[str, Any],
    update_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = []
    if source_scope_audit.get("passed") is not True:
        issues.append(_issue(
            "error",
            "source_scope_audit_not_passed",
            "source scope audit must have no errors",
            "source_scope_audit.passed",
        ))
    if approval_review.get("passed") is not True:
        issues.append(_issue(
            "error",
            "approval_review_not_passed",
            "source review approval must pass",
            "approval_review.passed",
        ))
    if update_plan.get("ready_for_registry_patch") is not True:
        issues.append(_issue(
            "error",
            "update_plan_not_ready",
            "registry update plan must be ready for patch review",
            "update_plan.ready_for_registry_patch",
        ))
    return issues


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


def _required_reviews(
    source_scope_audit: dict[str, Any],
    approval_review: dict[str, Any],
    update_plan: dict[str, Any],
) -> list[str]:
    reviews = []
    if source_scope_audit.get("passed") is not True:
        reviews.append("Resolve source scope audit errors.")
    reviews.extend(_strings(approval_review.get("required_reviews")))
    if update_plan.get("ready_for_registry_patch") is not True:
        reviews.extend(_update_plan_reviews(update_plan))
    return _unique(reviews)


def _update_plan_reviews(update_plan: dict[str, Any]) -> list[str]:
    reviews = []
    for issue in _dicts(update_plan.get("issues")):
        code = issue.get("code")
        if code == "approval_review_not_ready":
            reviews.append(
                "Pass source review approval before registry patch planning."
            )
        elif code == "source_not_found":
            reviews.append("Register the source before planning metadata patch.")
        else:
            reviews.append("Resolve registry update plan blockers.")
    return reviews


def _unique(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _single_value_list(value: Any) -> list[str]:
    return [value] if isinstance(value, str) and value else []


def _ints(value: Any) -> list[int]:
    return [item for item in value if isinstance(item, int)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _non_goals() -> list[str]:
    return [
        "Does not modify sources.json.",
        "Does not approve source review by itself.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
