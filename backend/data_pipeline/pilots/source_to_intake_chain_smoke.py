"""Stdlib-only smoke for source approval through intake readiness."""

from typing import Any


def build_source_to_intake_chain_smoke(
    *,
    source_review_chain: dict[str, Any],
    registry_patch_chain: dict[str, Any],
    snapshot_planning_review: dict[str, Any],
    intake_review: dict[str, Any],
) -> dict[str, Any]:
    """Check the no-write chain from source approval to intake readiness."""
    checks = {
        "source_review_chain_passed": source_review_chain.get("passed") is True,
        "source_review_update_plan_ready": (
            _nested_bool(source_review_chain, "checks", "update_plan_ready")
        ),
        "patch_chain_passed": registry_patch_chain.get("passed") is True,
        "patch_chain_registry_not_modified": (
            _nested_bool(registry_patch_chain, "checks", "registry_not_modified")
        ),
        "snapshot_planning_ready": (
            snapshot_planning_review.get("ready_for_snapshot_planning") is True
        ),
        "intake_ready": intake_review.get("ready_for_snapshot") is True,
        "source_id_consistent": _source_id_consistent(
            source_review_chain,
            registry_patch_chain,
            snapshot_planning_review,
            intake_review,
        ),
        "scope_consistent": _scope_consistent(
            source_review_chain,
            snapshot_planning_review,
            intake_review,
        ),
    }
    issues = _issues_from_checks(checks)
    issue_counts = {
        "error": len(issues),
        "warning": 0,
        "info": 0,
    }
    return {
        "action": "source_to_intake_chain_smoke",
        "passed": issue_counts["error"] == 0,
        "scope": _scope(source_review_chain, intake_review),
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(
            source_review_chain,
            registry_patch_chain,
            snapshot_planning_review,
            intake_review,
        ),
        "reviews": {
            "source_review_chain": source_review_chain,
            "registry_patch_chain": registry_patch_chain,
            "snapshot_planning": snapshot_planning_review,
            "intake": intake_review,
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
    source_review_chain: dict[str, Any],
    registry_patch_chain: dict[str, Any],
    snapshot_planning_review: dict[str, Any],
    intake_review: dict[str, Any],
) -> bool:
    source_id = _scope_value(source_review_chain, "source_id")
    if not isinstance(source_id, str) or not source_id:
        return False
    matching_source_ids = _nested_list(
        snapshot_planning_review,
        "source_summary",
        "matching_source_ids",
    )
    return (
        registry_patch_chain.get("source_id") == source_id
        and source_id in matching_source_ids
        and _nested_value(intake_review, "scope", "source_id") == source_id
    )


def _scope_consistent(
    source_review_chain: dict[str, Any],
    snapshot_planning_review: dict[str, Any],
    intake_review: dict[str, Any],
) -> bool:
    source_scope = _dict(source_review_chain.get("scope"))
    planning_scope = _dict(snapshot_planning_review.get("scope"))
    intake_scope = _dict(intake_review.get("scope"))
    return (
        source_scope.get("data_category") == planning_scope.get("data_category")
        == intake_scope.get("dataset")
        and source_scope.get("province") == planning_scope.get("province")
        == intake_scope.get("province")
        and _first_year(source_scope.get("years")) == planning_scope.get("year")
        == intake_scope.get("published_year")
    )


def _scope(
    source_review_chain: dict[str, Any],
    intake_review: dict[str, Any],
) -> dict[str, Any]:
    source_scope = _dict(source_review_chain.get("scope"))
    intake_scope = _dict(intake_review.get("scope"))
    return {
        "source_id": source_scope.get("source_id") or intake_scope.get("source_id"),
        "dataset": source_scope.get("data_category") or intake_scope.get("dataset"),
        "province": source_scope.get("province") or intake_scope.get("province"),
        "year": _first_year(source_scope.get("years"))
        or intake_scope.get("published_year"),
    }


def _issues_from_checks(checks: dict[str, bool]) -> list[dict[str, str]]:
    issues = []
    for check, passed in checks.items():
        if not passed:
            issues.append({
                "severity": "error",
                "code": f"{check}_failed",
                "message": f"source-to-intake chain check failed: {check}",
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


def _scope_value(payload: dict[str, Any], field: str) -> Any:
    return _nested_value(payload, "scope", field)


def _nested_bool(payload: dict[str, Any], parent: str, child: str) -> bool:
    return _nested_value(payload, parent, child) is True


def _nested_value(payload: dict[str, Any], parent: str, child: str) -> Any:
    parent_value = payload.get(parent)
    if isinstance(parent_value, dict):
        return parent_value.get(child)
    return None


def _nested_list(payload: dict[str, Any], parent: str, child: str) -> list[Any]:
    value = _nested_value(payload, parent, child)
    return value if isinstance(value, list) else []


def _first_year(value: Any) -> Any:
    if not isinstance(value, list) or not value:
        return None
    return value[0]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
