"""Review whether reviewed real data can become Agent-visible."""

from typing import Any


def review_agent_visibility_activation(
    *,
    artifact_manifest: dict[str, Any],
    answer_policy_review: dict[str, Any] | None = None,
    activation_approval: dict[str, Any] | None = None,
    loader_run_evidence_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a no-write Agent visibility activation review report."""
    issues = []
    issues.extend(_artifact_manifest_issues(artifact_manifest))
    issues.extend(_answer_policy_issues(answer_policy_review))
    issues.extend(_activation_approval_issues(
        activation_approval,
        artifact_manifest,
        loader_run_evidence_review,
    ))

    issue_counts = _issue_counts(issues)
    ready = issue_counts["error"] == 0
    return {
        "action": "agent_visibility_activation_review",
        "passed": ready,
        "ready_for_agent_visibility": ready,
        "scope": _scope(artifact_manifest),
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues, ready),
        "non_goals": _non_goals(),
    }


def _artifact_manifest_issues(
    artifact_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = []
    if artifact_manifest.get("ready_for_loader_execution") is not True:
        issues.append(_issue(
            "error",
            "artifact_manifest_not_loader_ready",
            "artifact manifest must be ready before Agent visibility review",
            "artifact_manifest.ready_for_loader_execution",
        ))
    loader_handoff = artifact_manifest.get("loader_handoff")
    loader_handoff = loader_handoff if isinstance(loader_handoff, dict) else {}
    if loader_handoff.get("requires_separate_loader_run_command") is not True:
        issues.append(_issue(
            "error",
            "loader_run_command_requirement_missing",
            "artifact manifest must require a separate loader run command",
            "artifact_manifest.loader_handoff.requires_separate_loader_run_command",
        ))
    return issues


def _answer_policy_issues(
    answer_policy_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if answer_policy_review is None:
        return [_issue(
            "error",
            "missing_answer_source_policy_review",
            "answer source policy review is required before Agent visibility",
            "answer_policy_review",
        )]

    issues = []
    if answer_policy_review.get("action") != "answer_source_policy_review":
        issues.append(_issue(
            "error",
            "invalid_answer_source_policy_review_action",
            "answer source policy review action is invalid",
            "answer_policy_review.action",
        ))
    if answer_policy_review.get("passed") is not True:
        issues.append(_issue(
            "error",
            "answer_source_policy_not_passed",
            "answer source policy review must pass before Agent visibility",
            "answer_policy_review.passed",
        ))

    policy = answer_policy_review.get("answer_source_policy")
    policy = policy if isinstance(policy, dict) else {}
    answer_mode = policy.get("answer_mode")
    if answer_mode == "unsupported":
        issues.append(_issue(
            "error",
            "answer_source_policy_unsupported",
            "unsupported answer source policy cannot become Agent-visible",
            "answer_policy_review.answer_source_policy.answer_mode",
        ))
    elif answer_mode == "citeable_with_caution":
        issues.append(_issue(
            "warning",
            "answer_source_policy_requires_caution",
            "Agent answers must cite sources and lower certainty",
            "answer_policy_review.answer_source_policy.answer_mode",
        ))
    elif answer_mode != "citeable":
        issues.append(_issue(
            "error",
            "answer_source_policy_unknown_mode",
            "answer source policy must be citeable or citeable_with_caution",
            "answer_policy_review.answer_source_policy.answer_mode",
        ))
    return issues


def _activation_approval_issues(
    activation_approval: dict[str, Any] | None,
    artifact_manifest: dict[str, Any],
    loader_run_evidence_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if activation_approval is None:
        return [_issue(
            "error",
            "missing_agent_visibility_approval",
            "separate Agent visibility approval is required",
            "activation_approval",
        )]

    issues = []
    if activation_approval.get("action") != "agent_visibility_approval":
        issues.append(_issue(
            "error",
            "invalid_agent_visibility_approval_action",
            "activation approval action is invalid",
            "activation_approval.action",
        ))
    if activation_approval.get("allow_agent_visibility") is not True:
        issues.append(_issue(
            "error",
            "agent_visibility_not_allowed",
            "activation approval must allow Agent visibility",
            "activation_approval.allow_agent_visibility",
        ))
    if activation_approval.get("loader_run_confirmed") is not True:
        issues.append(_issue(
            "error",
            "loader_run_not_confirmed",
            "canonical loader run must be separately confirmed",
            "activation_approval.loader_run_confirmed",
        ))
    else:
        issues.extend(_loader_run_evidence_issues(
            activation_approval,
            artifact_manifest,
            loader_run_evidence_review,
        ))
    if not activation_approval.get("reviewed_by"):
        issues.append(_issue(
            "error",
            "missing_agent_visibility_reviewer",
            "activation approval must include reviewed_by",
            "activation_approval.reviewed_by",
        ))
    if not activation_approval.get("reviewed_at"):
        issues.append(_issue(
            "error",
            "missing_agent_visibility_reviewed_at",
            "activation approval must include reviewed_at",
            "activation_approval.reviewed_at",
        ))
    issues.extend(_approval_scope_issues(activation_approval, artifact_manifest))
    return issues


def _loader_run_evidence_issues(
    activation_approval: dict[str, Any],
    artifact_manifest: dict[str, Any],
    loader_run_evidence_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    evidence = activation_approval.get("loader_run_evidence")
    issues: list[dict[str, Any]] = []
    issues.extend(_loader_run_evidence_review_issues(
        artifact_manifest,
        evidence,
        loader_run_evidence_review,
    ))
    if not isinstance(evidence, dict):
        issues.append(_issue(
            "error",
            "missing_loader_run_evidence",
            "activation approval must include loader_run_evidence",
            "activation_approval.loader_run_evidence",
        ))
        return issues

    for field in ("run_id", "completed_at", "artifact_manifest_path", "result_status"):
        if not evidence.get(field):
            issues.append(_issue(
                "error",
                f"missing_loader_run_evidence_{field}",
                f"loader_run_evidence.{field} is required",
                f"activation_approval.loader_run_evidence.{field}",
            ))

    if evidence.get("result_status") != "succeeded":
        issues.append(_issue(
            "error",
            "loader_run_not_succeeded",
            "loader_run_evidence.result_status must be succeeded",
            "activation_approval.loader_run_evidence.result_status",
        ))

    loaded_counts = evidence.get("loaded_counts")
    if not isinstance(loaded_counts, dict) or not loaded_counts:
        issues.append(_issue(
            "error",
            "missing_loader_run_loaded_counts",
            "loader_run_evidence.loaded_counts must be a non-empty object",
            "activation_approval.loader_run_evidence.loaded_counts",
        ))
        return issues

    expected_count = artifact_manifest.get("candidate_count")
    loaded_count = sum(
        count for count in loaded_counts.values() if isinstance(count, int)
    )
    if isinstance(expected_count, int) and loaded_count != expected_count:
        issues.append(_issue(
            "error",
            "loader_run_candidate_count_mismatch",
            "loader_run_evidence loaded count must match artifact manifest",
            "activation_approval.loader_run_evidence.loaded_counts",
        ))
    return issues


def _loader_run_evidence_review_issues(
    artifact_manifest: dict[str, Any],
    approval_evidence: object,
    loader_run_evidence_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if loader_run_evidence_review is None:
        return [_issue(
            "error",
            "missing_loader_run_evidence_review",
            "loader run evidence review is required before Agent visibility",
            "loader_run_evidence_review",
        )]

    issues = []
    if loader_run_evidence_review.get("action") != "loader_run_evidence_review":
        issues.append(_issue(
            "error",
            "invalid_loader_run_evidence_review_action",
            "loader run evidence review action is invalid",
            "loader_run_evidence_review.action",
        ))
    if loader_run_evidence_review.get("passed") is not True:
        issues.append(_issue(
            "error",
            "loader_run_evidence_review_not_passed",
            "loader run evidence review must pass before Agent visibility",
            "loader_run_evidence_review.passed",
        ))
    if loader_run_evidence_review.get("ready_for_activation_evidence") is not True:
        issues.append(_issue(
            "error",
            "loader_run_evidence_review_not_ready",
            "loader run evidence review must be activation-ready",
            "loader_run_evidence_review.ready_for_activation_evidence",
        ))

    review_scope = loader_run_evidence_review.get("scope")
    review_scope = review_scope if isinstance(review_scope, dict) else {}
    for field in ("source_id", "snapshot_id", "dataset", "candidate_count"):
        if review_scope.get(field) != artifact_manifest.get(field):
            issues.append(_issue(
                "error",
                f"loader_run_evidence_review_scope_{field}_mismatch",
                f"loader run evidence review {field} does not match manifest",
                f"loader_run_evidence_review.scope.{field}",
            ))

    review_evidence = loader_run_evidence_review.get("loader_run_evidence")
    if isinstance(approval_evidence, dict) and review_evidence != approval_evidence:
        issues.append(_issue(
            "error",
            "loader_run_evidence_review_mismatch",
            "activation approval evidence must match loader run evidence review",
            "activation_approval.loader_run_evidence",
        ))
    return issues


def _approval_scope_issues(
    activation_approval: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    approval_scope = activation_approval.get("scope")
    if not isinstance(approval_scope, dict):
        return [_issue(
            "error",
            "missing_agent_visibility_approval_scope",
            "activation approval scope is required",
            "activation_approval.scope",
        )]

    issues = []
    for field in ("source_id", "snapshot_id", "dataset"):
        expected = artifact_manifest.get(field)
        actual = approval_scope.get(field)
        if expected != actual:
            issues.append(_issue(
                "error",
                f"agent_visibility_scope_{field}_mismatch",
                f"activation approval {field} does not match artifact manifest",
                f"activation_approval.scope.{field}",
            ))
    return issues


def _scope(artifact_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": artifact_manifest.get("source_id"),
        "snapshot_id": artifact_manifest.get("snapshot_id"),
        "dataset": artifact_manifest.get("dataset"),
        "candidate_count": artifact_manifest.get("candidate_count"),
    }


def _issue(
    severity: str,
    code: str,
    message: str,
    field: str,
) -> dict[str, str]:
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
    issues: list[dict[str, Any]],
    ready: bool,
) -> list[str]:
    codes = {issue["code"] for issue in issues}
    if ready:
        reviews = []
        if "answer_source_policy_requires_caution" in codes:
            reviews.append("Configure Agent answers to cite sources and lower certainty.")
        reviews.append("Run a separately approved Agent/RAG refresh if needed.")
        return reviews

    reviews = []
    if "artifact_manifest_not_loader_ready" in codes:
        reviews.append("Resolve artifact manifest readiness first.")
    if "missing_answer_source_policy_review" in codes:
        reviews.append("Generate answer source policy review.")
    if "answer_source_policy_not_passed" in codes:
        reviews.append("Resolve answer source policy blockers.")
    if "missing_agent_visibility_approval" in codes:
        reviews.append("Provide separate Agent visibility approval.")
    if "agent_visibility_not_allowed" in codes:
        reviews.append("Confirm Agent visibility approval explicitly allows activation.")
    if "loader_run_not_confirmed" in codes:
        reviews.append("Confirm the approved canonical loader run.")
    if (
        "missing_agent_visibility_reviewer" in codes
        or "missing_agent_visibility_reviewed_at" in codes
    ):
        reviews.append("Record Agent visibility reviewer and review time.")
    if "missing_loader_run_evidence" in codes:
        reviews.append("Attach canonical loader run evidence.")
    if "missing_loader_run_evidence_review" in codes:
        reviews.append("Generate loader run evidence review.")
    if "loader_run_evidence_review_mismatch" in codes:
        reviews.append("Use loader evidence from the passed evidence review.")
    if "loader_run_candidate_count_mismatch" in codes:
        reviews.append("Resolve loader run evidence count mismatch.")
    if not reviews:
        reviews.append("Resolve Agent visibility activation issues.")
    return reviews


def _non_goals() -> list[str]:
    return [
        "Does not execute crawler.",
        "Does not write canonical database rows.",
        "Does not modify seed data.",
        "Does not refresh RAG or Agent-visible data.",
        "Does not replace separate deployment or rollback review.",
    ]
