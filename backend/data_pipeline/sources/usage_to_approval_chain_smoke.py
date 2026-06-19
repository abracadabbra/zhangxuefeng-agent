"""Stdlib-only smoke from source usage review to source approval readiness."""

from __future__ import annotations

from typing import Any


def build_usage_to_approval_chain_smoke(
    *,
    usage_review: dict[str, Any],
    source_approval_review: dict[str, Any],
) -> dict[str, Any]:
    """Check usage/citation review and source approval evidence continuity."""
    checks = {
        "usage_review_passed": usage_review.get("passed") is True,
        "usage_review_ready": (
            usage_review.get("ready_for_source_approval_license_review") is True
        ),
        "source_approval_passed": source_approval_review.get("passed") is True,
        "source_approval_ready": (
            source_approval_review.get("ready_for_registry_update") is True
        ),
        "source_id_consistent": _source_id_consistent(
            usage_review,
            source_approval_review,
        ),
        "scope_consistent": _scope_consistent(
            usage_review,
            source_approval_review,
        ),
        "approval_evidence_uses_ready_usage_review": (
            _approval_evidence_uses_ready_usage_review(source_approval_review)
        ),
        "registry_update_hint_matches_approval_scope": (
            _registry_update_hint_matches_approval_scope(source_approval_review)
        ),
    }
    issues = _issues_from_checks(checks)
    issue_counts = {"error": len(issues), "warning": 0, "info": 0}
    return {
        "action": "source_usage_to_approval_chain_smoke",
        "passed": issue_counts["error"] == 0,
        "scope": _scope(usage_review, source_approval_review),
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(usage_review, source_approval_review),
        "reviews": {
            "source_usage_review": usage_review,
            "source_approval_review": source_approval_review,
        },
        "non_goals": [
            "Does not modify sources.json.",
            "Does not approve any real source.",
            "Does not fetch remote data or download official attachments.",
            "Does not create raw snapshots.",
            "Does not parse rows or run quality gates.",
            "Does not execute canonical loader.",
            "Does not write database rows, seed data, RAG indexes, or Agent data.",
        ],
    }


def _source_id_consistent(
    usage_review: dict[str, Any],
    source_approval_review: dict[str, Any],
) -> bool:
    usage_scope = _object(usage_review.get("scope"))
    approval_scope = _object(source_approval_review.get("scope"))
    return usage_scope.get("source_id") == approval_scope.get("source_id")


def _scope_consistent(
    usage_review: dict[str, Any],
    source_approval_review: dict[str, Any],
) -> bool:
    usage_scope = _object(usage_review.get("scope"))
    approval_scope = _object(source_approval_review.get("scope"))
    return {
        "data_category": usage_scope.get("data_category"),
        "province": usage_scope.get("province"),
        "years": _list(usage_scope.get("years")),
    } == {
        "data_category": approval_scope.get("data_category"),
        "province": approval_scope.get("province"),
        "years": _list(approval_scope.get("years")),
    }


def _approval_evidence_uses_ready_usage_review(
    source_approval_review: dict[str, Any],
) -> bool:
    evidence_summary = _object(source_approval_review.get("evidence_summary"))
    return (
        evidence_summary.get("has_usage_review") is True
        and evidence_summary.get("usage_review_ready") is True
    )


def _registry_update_hint_matches_approval_scope(
    source_approval_review: dict[str, Any],
) -> bool:
    approval_scope = _object(source_approval_review.get("scope"))
    update_hint = _object(source_approval_review.get("registry_update_hint"))
    return (
        update_hint.get("can_update_registry") is True
        and update_hint.get("source_id") == approval_scope.get("source_id")
        and update_hint.get("target_review_status")
        == approval_scope.get("target_review_status")
        and update_hint.get("add_data_category_if_missing")
        == approval_scope.get("data_category")
        and update_hint.get("add_province_if_missing") == approval_scope.get("province")
        and _list(update_hint.get("add_years_if_missing"))
        == _list(approval_scope.get("years"))
    )


def _scope(
    usage_review: dict[str, Any],
    source_approval_review: dict[str, Any],
) -> dict[str, Any]:
    usage_scope = _object(usage_review.get("scope"))
    approval_scope = _object(source_approval_review.get("scope"))
    return {
        "source_id": usage_scope.get("source_id") or approval_scope.get("source_id"),
        "data_category": (
            usage_scope.get("data_category") or approval_scope.get("data_category")
        ),
        "province": usage_scope.get("province") or approval_scope.get("province"),
        "years": _list(usage_scope.get("years") or approval_scope.get("years")),
        "target_review_status": approval_scope.get("target_review_status"),
    }


def _issues_from_checks(checks: dict[str, bool]) -> list[dict[str, str]]:
    issues = []
    for check, passed in checks.items():
        if not passed:
            issues.append({
                "severity": "error",
                "code": f"{check}_failed",
                "message": f"usage-to-approval chain check failed: {check}",
                "field": f"checks.{check}",
            })
    return issues


def _required_reviews(*reviews: dict[str, Any]) -> list[str]:
    aggregated = []
    seen = set()
    for review in reviews:
        for item in review.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                aggregated.append(item)
                seen.add(item)
    return aggregated


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
