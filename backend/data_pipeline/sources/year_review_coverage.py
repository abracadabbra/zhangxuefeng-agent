"""No-write coverage report for priority source year review packets."""

from __future__ import annotations

from typing import Any


def build_source_year_review_coverage_report(
    coverage_report: dict[str, Any],
    year_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize whether missing priority years have human review packets."""
    required_provinces = _str_list(
        _object(coverage_report.get("gap_summary")).get(
            "priority_provinces_without_years",
        ),
    )
    review_by_province = _review_by_province(year_reviews)
    missing_reviews = [
        province for province in required_provinces if province not in review_by_province
    ]
    blocked_reviews = [
        province for province in required_provinces
        if _review_ready(review_by_province.get(province)) is False
    ]
    ready_reviews = [
        province for province in required_provinces
        if _review_ready(review_by_province.get(province)) is True
    ]
    issues = _issues(missing_reviews, blocked_reviews)
    issue_counts = _issue_counts(issues)
    ready = not missing_reviews and not blocked_reviews and not issue_counts["error"]
    return {
        "action": "source_year_review_coverage_report",
        "passed": ready,
        "ready_for_priority_source_year_registration": ready,
        "next_gate": _next_gate(missing_reviews, blocked_reviews),
        "scope": {
            "required_provinces": required_provinces,
            "data_categories": _str_list(
                _object(coverage_report.get("priority_scope")).get(
                    "data_categories",
                ),
            ),
        },
        "current_state": {
            "coverage_report_passed": coverage_report.get("passed") is True,
            "required_province_count": len(required_provinces),
            "review_artifact_count": len(review_by_province),
            "ready_review_count": len(ready_reviews),
            "blocked_review_count": len(blocked_reviews),
            "missing_review_count": len(missing_reviews),
        },
        "reviewed_provinces": sorted(review_by_province),
        "ready_reviews": ready_reviews,
        "blocked_reviews": blocked_reviews,
        "missing_reviews": missing_reviews,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(missing_reviews, blocked_reviews),
        "non_goals": [
            "Does not modify sources.json.",
            "Does not register source years.",
            "Does not approve sources, usage, or registry patches.",
            "Does not fetch remote source pages or download attachments.",
            "Does not create raw snapshots.",
            "Does not parse rows or run quality gates.",
            "Does not execute loader or write databases.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _review_by_province(
    year_reviews: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    reviews: dict[str, dict[str, Any]] = {}
    for review in year_reviews:
        if review.get("action") != "source_year_review":
            continue
        scope = _object(review.get("scope"))
        province = scope.get("province")
        if isinstance(province, str) and province:
            reviews[province] = review
    return reviews


def _review_ready(review: dict[str, Any] | None) -> bool | None:
    if review is None:
        return None
    return review.get("ready_for_source_year_registration") is True


def _issues(
    missing_reviews: list[str],
    blocked_reviews: list[str],
) -> list[dict[str, str]]:
    issues = []
    for province in missing_reviews:
        issues.append({
            "severity": "warning",
            "code": "missing_source_year_review",
            "message": f"priority province has no source year review: {province}",
            "field": f"year_reviews.{province}",
        })
    for province in blocked_reviews:
        issues.append({
            "severity": "warning",
            "code": "source_year_review_not_ready",
            "message": f"priority source year review is not ready: {province}",
            "field": f"year_reviews.{province}",
        })
    return issues


def _issue_counts(issues: list[dict[str, str]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _required_reviews(
    missing_reviews: list[str],
    blocked_reviews: list[str],
) -> list[str]:
    reviews = []
    if missing_reviews:
        reviews.append("Create source year review packets for priority provinces.")
    if blocked_reviews:
        reviews.append("Complete blocked priority source year reviews.")
    return reviews


def _next_gate(missing_reviews: list[str], blocked_reviews: list[str]) -> str:
    if missing_reviews:
        return "collect_priority_source_year_reviews"
    if blocked_reviews:
        return "complete_priority_source_year_reviews"
    return "source_registry_year_update_plan"


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
