"""No-write action queue for priority source coverage gaps."""

from __future__ import annotations

from typing import Any


def build_priority_source_coverage_action_queue(
    coverage_report: dict[str, Any],
) -> dict[str, Any]:
    """Turn priority source coverage gaps into human review actions."""
    gap_summary = _object(coverage_report.get("gap_summary"))
    priority_scope = _object(coverage_report.get("priority_scope"))
    readiness = _object(coverage_report.get("readiness"))
    actions = (
        _missing_province_actions(gap_summary)
        + _missing_year_actions(gap_summary)
        + _source_approval_actions(gap_summary)
    )
    issue_counts = {
        "error": len([item for item in actions if item["status"] == "blocked"]),
        "warning": len([item for item in actions if item["status"] == "pending"]),
        "info": 0,
    }
    return {
        "action": "priority_source_coverage_action_queue",
        "passed": not actions,
        "ready_for_human_review": bool(actions),
        "next_gate": _next_gate(gap_summary),
        "scope": {
            "provinces": _str_list(priority_scope.get("provinces")),
            "data_categories": _str_list(priority_scope.get("data_categories")),
        },
        "current_state": {
            "coverage_report_passed": coverage_report.get("passed") is True,
            "ready_for_snapshot_planning": (
                readiness.get("ready_for_snapshot_planning") is True
            ),
            "missing_priority_province_count": len(
                _str_list(gap_summary.get("missing_priority_provinces")),
            ),
            "priority_province_without_year_count": len(
                _str_list(gap_summary.get("priority_provinces_without_years")),
            ),
            "priority_province_without_approved_source_count": len(
                _str_list(
                    gap_summary.get("priority_provinces_without_approved_source"),
                ),
            ),
        },
        "priority_actions": actions,
        "issue_counts": issue_counts,
        "issues": _issues(actions),
        "required_reviews": _required_reviews(actions),
        "non_goals": [
            "Does not modify sources.json.",
            "Does not approve any source or registered year.",
            "Does not fetch remote source pages or download attachments.",
            "Does not create raw snapshots.",
            "Does not parse rows or run quality gates.",
            "Does not execute loader or write databases.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _missing_province_actions(
    gap_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": f"register_priority_source:{province}",
            "phase": "source_registry",
            "status": "blocked",
            "province": province,
            "instruction": (
                "Register an official or authorized homepage candidate for "
                f"{province} before dataset review."
            ),
            "blocks": "priority_source_coverage",
            "source": "priority_source_coverage_report.json",
        }
        for province in _str_list(gap_summary.get("missing_priority_provinces"))
    ]


def _missing_year_actions(gap_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"review_dataset_year:{province}",
            "phase": "source_review",
            "status": "pending",
            "province": province,
            "instruction": (
                f"Review official dataset years for {province} after "
                "usage/citation evidence is recorded."
            ),
            "blocks": "source_snapshot_planning",
            "source": "priority_source_coverage_report.json",
        }
        for province in _str_list(
            gap_summary.get("priority_provinces_without_years"),
        )
    ]


def _source_approval_actions(
    gap_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": f"complete_source_approval:{province}",
            "phase": "source_approval",
            "status": "pending",
            "province": province,
            "instruction": (
                f"Complete usage/citation and source approval for {province} "
                "before snapshot planning."
            ),
            "blocks": "source_snapshot_planning",
            "source": "priority_source_coverage_report.json",
        }
        for province in _str_list(
            gap_summary.get("priority_provinces_without_approved_source"),
        )
    ]


def _next_gate(gap_summary: dict[str, Any]) -> str:
    if _str_list(gap_summary.get("missing_priority_provinces")):
        return "register_priority_sources"
    if _str_list(gap_summary.get("priority_provinces_without_years")):
        return "review_priority_dataset_years"
    if _str_list(gap_summary.get("priority_provinces_without_approved_source")):
        return "complete_priority_source_approval"
    return "source_snapshot_planning"


def _issues(actions: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues = []
    for item in actions:
        status = item.get("status")
        if status not in {"blocked", "pending"}:
            continue
        issues.append({
            "severity": "error" if status == "blocked" else "warning",
            "code": f"{item.get('id')}_{status}",
            "message": str(item.get("instruction") or item.get("id")),
            "field": f"priority_actions.{item.get('id')}",
        })
    return issues


def _required_reviews(actions: list[dict[str, Any]]) -> list[str]:
    reviews = []
    if any(item["phase"] == "source_registry" for item in actions):
        reviews.append("Register missing priority province source candidates.")
    if any(item["id"].startswith("review_dataset_year:") for item in actions):
        reviews.append("Review official dataset pages and candidate years.")
    if any(item["id"].startswith("complete_source_approval:") for item in actions):
        reviews.append("Complete usage/citation and source approval reviews.")
    return reviews


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
