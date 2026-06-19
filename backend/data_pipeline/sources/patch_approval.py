"""No-write review for source registry patch approval packets."""

from typing import Any


ERROR = "error"


def review_source_registry_patch_approval(
    update_plan: dict[str, Any],
    approval_payload: dict[str, Any],
) -> dict[str, Any]:
    """Review whether a planned source registry patch is approved to execute."""
    issues: list[dict[str, Any]] = []
    _check_update_plan(update_plan, issues)
    _check_approval_payload(approval_payload, update_plan, issues)

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    return {
        "action": "source_registry_patch_approval_review",
        "passed": ready,
        "ready_for_registry_patch_execution": ready,
        "source_id": _source_id(update_plan, approval_payload),
        "planned_updates_summary": _planned_updates_summary(update_plan),
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


def _check_approval_payload(
    approval: dict[str, Any],
    update_plan: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if approval.get("action") != "source_registry_patch_approval":
        _issue(
            issues,
            "invalid_patch_approval_action",
            "approval action must be source_registry_patch_approval",
            "approval.action",
        )
    if approval.get("allow_source_registry_patch") is not True:
        _issue(
            issues,
            "source_registry_patch_not_allowed",
            "allow_source_registry_patch must be true",
            "approval.allow_source_registry_patch",
        )
    _require_value(approval, "source_id", issues, prefix="approval")
    if approval.get("source_id") != update_plan.get("source_id"):
        _issue(
            issues,
            "source_id_mismatch",
            "approval source_id must match update plan source_id",
            "approval.source_id",
        )
    _require_true(
        approval,
        "planned_updates_confirmed",
        issues,
        prefix="approval",
    )
    _require_value(approval, "reviewed_by", issues, prefix="approval")
    _require_value(approval, "reviewed_at", issues, prefix="approval")


def _planned_updates_summary(update_plan: dict[str, Any]) -> dict[str, Any]:
    planned_updates = update_plan.get("planned_updates")
    if not isinstance(planned_updates, dict):
        planned_updates = {}
    return {
        "review_status": _dict(planned_updates.get("review_status")),
        "data_categories": _dict(planned_updates.get("data_categories")),
        "coverage_provinces": _dict(planned_updates.get("coverage_provinces")),
        "coverage_years": _dict(planned_updates.get("coverage_years")),
    }


def _source_id(
    update_plan: dict[str, Any],
    approval_payload: dict[str, Any],
) -> Any:
    return update_plan.get("source_id") or approval_payload.get("source_id")


def _require_value(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    prefix: str,
) -> None:
    value = payload.get(field)
    if value is None or value == "":
        qualified = f"{prefix}.{field}"
        _issue(
            issues,
            f"missing_{qualified.replace('.', '_')}",
            f"{qualified} is required",
            qualified,
        )


def _require_true(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    prefix: str,
) -> None:
    if payload.get(field) is not True:
        qualified = f"{prefix}.{field}"
        _issue(
            issues,
            f"{qualified.replace('.', '_')}_not_confirmed",
            f"{qualified} must be true",
            qualified,
        )


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
        "invalid_update_plan_action": (
            "Provide a source_registry_update_plan artifact."
        ),
        "update_plan_not_ready": "Resolve source registry update plan blockers.",
        "missing_planned_updates": "Provide planned registry updates.",
        "invalid_patch_approval_action": (
            "Use a source_registry_patch_approval packet."
        ),
        "source_registry_patch_not_allowed": (
            "Set allow_source_registry_patch=true only after human review."
        ),
        "missing_approval_source_id": "Provide the approved source_id.",
        "source_id_mismatch": (
            "Match approval source_id to the registry update plan."
        ),
        "approval_planned_updates_confirmed_not_confirmed": (
            "Confirm the planned registry updates."
        ),
        "missing_approval_reviewed_by": "Provide registry patch reviewer.",
        "missing_approval_reviewed_at": (
            "Provide registry patch review date or timestamp."
        ),
    }
    return reviews.get(code)


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
