"""Stdlib-only smoke review for the synthetic real-data example chain."""

from typing import Any

from backend.data_pipeline.activation.review import review_agent_visibility_activation
from backend.data_pipeline.activation.loader_evidence import (
    build_loader_run_evidence_review,
)
from backend.data_pipeline.intake.review import review_intake_payload
from backend.data_pipeline.lineage.policy import build_answer_source_policy
from backend.data_pipeline.pilots.artifact_smoke import (
    build_pilot_artifact_smoke_review,
)


def build_example_chain_smoke_report(
    *,
    intake_payload: dict[str, Any],
    artifact_manifest: dict[str, Any],
    tool_response: dict[str, Any],
    expected_activation_review: dict[str, Any] | None = None,
    expected_source_id: str | None = None,
    expected_snapshot_id: str | None = None,
    expected_dataset: str | None = None,
    activation_approval: dict[str, Any] | None = None,
    loader_run_record: dict[str, Any] | None = None,
    parser_smoke_review: dict[str, Any] | None = None,
    quality_smoke_review: dict[str, Any] | None = None,
    artifact_manifest_path: str | None = None,
) -> dict[str, Any]:
    """Review the checked-in real-data example chain without runtime deps."""
    intake_review = review_intake_payload(intake_payload)
    artifact_smoke = build_pilot_artifact_smoke_review(
        artifact_manifest,
        expected_source_id=expected_source_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_dataset=expected_dataset,
    )
    answer_policy_review = _build_answer_policy_review(tool_response)
    activation_review = review_agent_visibility_activation(
        artifact_manifest=artifact_manifest,
        answer_policy_review=answer_policy_review,
    )
    loader_run_evidence_review = _build_loader_run_evidence_review(
        artifact_manifest=artifact_manifest,
        loader_run_record=loader_run_record,
        artifact_manifest_path=artifact_manifest_path,
    )
    activation_review_with_approval = _build_activation_review_with_approval(
        artifact_manifest=artifact_manifest,
        answer_policy_review=answer_policy_review,
        activation_approval=activation_approval,
        loader_run_evidence_review=loader_run_evidence_review,
    )

    checks = {
        "intake_ready": (
            intake_review.get("passed") is True
            and intake_review.get("ready_for_snapshot") is True
        ),
        "intake_snapshot_planning_ready": (
            _review_value(
                intake_review,
                "snapshot_planning_review",
                "ready_for_snapshot_planning",
            )
            is True
        ),
        "intake_required_reviews_empty": (
            intake_review.get("required_reviews") == []
        ),
        "intake_source_bound_to_expected_source": (
            expected_source_id is None
            or _expected_source_bound(intake_review, expected_source_id)
        ),
        "artifact_manifest_smoke_passed": artifact_smoke.get("passed") is True,
        "parser_smoke_ready_when_provided": (
            parser_smoke_review is None
            or (
                parser_smoke_review.get("passed") is True
                and parser_smoke_review.get("ready_for_parser") is True
            )
        ),
        "parser_smoke_scope_matches_when_provided": (
            parser_smoke_review is None
            or _parser_smoke_scope_matches(parser_smoke_review, artifact_manifest)
        ),
        "quality_smoke_ready_when_provided": (
            quality_smoke_review is None
            or (
                quality_smoke_review.get("passed") is True
                and quality_smoke_review.get("ready_for_quality_gate") is True
            )
        ),
        "quality_smoke_scope_matches_when_provided": (
            quality_smoke_review is None
            or _quality_smoke_scope_matches(quality_smoke_review, artifact_manifest)
        ),
        "answer_policy_passed": answer_policy_review.get("passed") is True,
        "answer_policy_citeable": (
            _review_value(
                answer_policy_review,
                "answer_source_policy",
                "answer_mode",
            )
            == "citeable"
        ),
        "activation_blocked_without_approval": _activation_is_blocked(
            activation_review,
        ),
        "loader_run_evidence_ready_when_provided": (
            loader_run_evidence_review is None
            or loader_run_evidence_review.get("ready_for_activation_evidence")
            is True
        ),
        "activation_with_approval_ready_when_provided": (
            activation_review_with_approval is None
            or activation_review_with_approval.get("ready_for_agent_visibility")
            is True
        ),
        "expected_activation_review_matches": (
            expected_activation_review is None
            or activation_review == expected_activation_review
        ),
    }
    issues = _issues_from_checks(checks)
    issue_counts = {
        "error": len(issues),
        "warning": 0,
        "info": 0,
    }
    return {
        "action": "real_data_example_chain_smoke",
        "passed": issue_counts["error"] == 0,
        "scope": {
            "source_id": artifact_manifest.get("source_id"),
            "snapshot_id": artifact_manifest.get("snapshot_id"),
            "dataset": artifact_manifest.get("dataset"),
            "candidate_count": artifact_manifest.get("candidate_count"),
        },
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _aggregate_required_reviews(
            artifact_manifest,
            intake_review,
            parser_smoke_review,
            quality_smoke_review,
            loader_run_evidence_review,
            activation_review,
            activation_review_with_approval,
        ),
        "reviews": {
            "intake": intake_review,
            "artifact_manifest": artifact_smoke,
            "parser_rows_bundle_smoke": parser_smoke_review,
            "quality_smoke": quality_smoke_review,
            "answer_policy": answer_policy_review,
            "loader_run_evidence": loader_run_evidence_review,
            "activation_without_approval": activation_review,
            "activation_with_approval": activation_review_with_approval,
        },
        "non_goals": [
            "Does not replace formal pydantic dry-run or artifact builders.",
            "Does not fetch remote data.",
            "Does not write database rows or seed data.",
            "Does not approve loader execution.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _build_answer_policy_review(tool_response: dict[str, Any]) -> dict[str, Any]:
    source_summary = tool_response.get("source_summary")
    if not isinstance(source_summary, dict):
        answer_policy = build_answer_source_policy(None)
        return {
            "action": "answer_source_policy_review",
            "passed": False,
            "source_summary": None,
            "answer_source_policy": answer_policy,
        }
    answer_policy = build_answer_source_policy(source_summary)
    return {
        "action": "answer_source_policy_review",
        "passed": answer_policy["answer_mode"] != "unsupported",
        "source_summary": source_summary,
        "answer_source_policy": answer_policy,
    }


def _activation_is_blocked(activation_review: dict[str, Any]) -> bool:
    issue_codes = {
        issue.get("code")
        for issue in activation_review.get("issues", [])
        if isinstance(issue, dict)
    }
    return (
        activation_review.get("ready_for_agent_visibility") is False
        and "missing_agent_visibility_approval" in issue_codes
    )


def _issues_from_checks(checks: dict[str, bool]) -> list[dict[str, str]]:
    issues = []
    for check, passed in checks.items():
        if not passed:
            issues.append({
                "severity": "error",
                "code": f"{check}_failed",
                "message": f"example chain check failed: {check}",
                "field": f"checks.{check}",
            })
    return issues


def _review_value(
    review: dict[str, Any],
    parent_key: str,
    child_key: str,
) -> Any:
    parent = review.get(parent_key)
    if isinstance(parent, dict):
        return parent.get(child_key)
    return None


def _expected_source_bound(
    intake_review: dict[str, Any],
    expected_source_id: str,
) -> bool:
    source_ids = _review_value(
        intake_review,
        "snapshot_planning_review",
        "source_summary",
    )
    if not isinstance(source_ids, dict):
        return False
    matching_source_ids = source_ids.get("matching_source_ids")
    return (
        isinstance(matching_source_ids, list)
        and expected_source_id in matching_source_ids
    )


def _parser_smoke_scope_matches(
    parser_smoke_review: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> bool:
    scope = parser_smoke_review.get("scope")
    if not isinstance(scope, dict):
        return False
    expectations = {
        "source_id": artifact_manifest.get("source_id"),
        "snapshot_id": artifact_manifest.get("snapshot_id"),
        "dataset": artifact_manifest.get("dataset"),
        "row_count": artifact_manifest.get("candidate_count"),
    }
    return all(scope.get(field) == expected for field, expected in expectations.items())


def _quality_smoke_scope_matches(
    quality_smoke_review: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> bool:
    scope = quality_smoke_review.get("scope")
    if not isinstance(scope, dict):
        return False
    expectations = {
        "source_id": artifact_manifest.get("source_id"),
        "snapshot_id": artifact_manifest.get("snapshot_id"),
        "dataset": artifact_manifest.get("dataset"),
        "candidate_count": artifact_manifest.get("candidate_count"),
    }
    return all(
        scope.get(field) == expected
        for field, expected in expectations.items()
    )


def _build_loader_run_evidence_review(
    *,
    artifact_manifest: dict[str, Any],
    loader_run_record: dict[str, Any] | None,
    artifact_manifest_path: str | None,
) -> dict[str, Any] | None:
    if loader_run_record is None or artifact_manifest_path is None:
        return None

    return build_loader_run_evidence_review(
        artifact_manifest=artifact_manifest,
        artifact_manifest_path=artifact_manifest_path,
        loader_run_record=loader_run_record,
    )


def _build_activation_review_with_approval(
    *,
    artifact_manifest: dict[str, Any],
    answer_policy_review: dict[str, Any],
    activation_approval: dict[str, Any] | None,
    loader_run_evidence_review: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if activation_approval is None or loader_run_evidence_review is None:
        return None

    return review_agent_visibility_activation(
        artifact_manifest=artifact_manifest,
        answer_policy_review=answer_policy_review,
        activation_approval=activation_approval,
        loader_run_evidence_review=loader_run_evidence_review,
    )


def _aggregate_required_reviews(*reviews: dict[str, Any] | None) -> list[str]:
    aggregated = []
    seen = set()
    for review in reviews:
        if not isinstance(review, dict):
            continue
        for item in review.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                aggregated.append(item)
                seen.add(item)
    return aggregated
