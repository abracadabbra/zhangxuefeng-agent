"""Review canonical loader run evidence before Agent visibility activation."""

from typing import Any


def build_loader_run_evidence_review(
    *,
    artifact_manifest: dict[str, Any],
    artifact_manifest_path: str,
    loader_run_record: dict[str, Any],
) -> dict[str, Any]:
    """Build a no-write review of a canonical loader run record."""
    issues: list[dict[str, Any]] = []
    issues.extend(_artifact_manifest_issues(artifact_manifest))
    issues.extend(_loader_run_record_issues(
        artifact_manifest=artifact_manifest,
        artifact_manifest_path=artifact_manifest_path,
        loader_run_record=loader_run_record,
    ))

    issue_counts = _issue_counts(issues)
    ready = issue_counts["error"] == 0
    return {
        "action": "loader_run_evidence_review",
        "passed": ready,
        "ready_for_activation_evidence": ready,
        "scope": _scope(artifact_manifest),
        "issue_counts": issue_counts,
        "issues": issues,
        "loader_run_evidence": _loader_run_evidence(loader_run_record),
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
            "artifact manifest must be loader-ready before run evidence review",
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


def _loader_run_record_issues(
    *,
    artifact_manifest: dict[str, Any],
    artifact_manifest_path: str,
    loader_run_record: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = []
    if loader_run_record.get("action") != "canonical_loader_run_record":
        issues.append(_issue(
            "error",
            "invalid_loader_run_record_action",
            "loader run record action is invalid",
            "loader_run_record.action",
        ))

    for field in ("run_id", "completed_at", "artifact_manifest_path"):
        if not loader_run_record.get(field):
            issues.append(_issue(
                "error",
                f"missing_loader_run_record_{field}",
                f"loader_run_record.{field} is required",
                f"loader_run_record.{field}",
            ))

    if loader_run_record.get("artifact_manifest_path") != artifact_manifest_path:
        issues.append(_issue(
            "error",
            "loader_run_record_manifest_path_mismatch",
            "loader run record artifact manifest path does not match input",
            "loader_run_record.artifact_manifest_path",
        ))

    entrypoint = loader_run_record.get("loader_entrypoint")
    if entrypoint != "load_candidates_after_artifact_manifest":
        issues.append(_issue(
            "error",
            "invalid_loader_run_entrypoint",
            "loader run must use load_candidates_after_artifact_manifest",
            "loader_run_record.loader_entrypoint",
        ))

    if loader_run_record.get("result_status") != "succeeded":
        issues.append(_issue(
            "error",
            "loader_run_not_succeeded",
            "loader run record result_status must be succeeded",
            "loader_run_record.result_status",
        ))

    issues.extend(_scope_issues(artifact_manifest, loader_run_record))
    issues.extend(_loaded_count_issues(artifact_manifest, loader_run_record))
    return issues


def _scope_issues(
    artifact_manifest: dict[str, Any],
    loader_run_record: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = []
    for field in ("source_id", "snapshot_id", "dataset"):
        expected = artifact_manifest.get(field)
        actual = loader_run_record.get(field)
        if expected != actual:
            issues.append(_issue(
                "error",
                f"loader_run_record_{field}_mismatch",
                f"loader run record {field} does not match artifact manifest",
                f"loader_run_record.{field}",
            ))
    return issues


def _loaded_count_issues(
    artifact_manifest: dict[str, Any],
    loader_run_record: dict[str, Any],
) -> list[dict[str, Any]]:
    loaded_counts = loader_run_record.get("loaded_counts")
    if not isinstance(loaded_counts, dict) or not loaded_counts:
        return [_issue(
            "error",
            "missing_loader_run_loaded_counts",
            "loader run record loaded_counts must be a non-empty object",
            "loader_run_record.loaded_counts",
        )]

    issues = []
    loaded_count = 0
    for entity_type, count in loaded_counts.items():
        if not isinstance(entity_type, str) or not entity_type:
            issues.append(_issue(
                "error",
                "invalid_loader_run_loaded_count_entity_type",
                "loaded_counts keys must be non-empty strings",
                "loader_run_record.loaded_counts",
            ))
        if not isinstance(count, int) or count < 0:
            issues.append(_issue(
                "error",
                "invalid_loader_run_loaded_count",
                "loaded_counts values must be non-negative integers",
                "loader_run_record.loaded_counts",
            ))
            continue
        loaded_count += count

    expected_count = artifact_manifest.get("candidate_count")
    if isinstance(expected_count, int) and loaded_count != expected_count:
        issues.append(_issue(
            "error",
            "loader_run_candidate_count_mismatch",
            "loader run loaded count must match artifact manifest candidate count",
            "loader_run_record.loaded_counts",
        ))
    return issues


def _loader_run_evidence(loader_run_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": loader_run_record.get("run_id"),
        "completed_at": loader_run_record.get("completed_at"),
        "artifact_manifest_path": loader_run_record.get("artifact_manifest_path"),
        "result_status": loader_run_record.get("result_status"),
        "loaded_counts": dict(loader_run_record.get("loaded_counts") or {}),
    }


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
    if ready:
        return [
            "Copy loader_run_evidence into the Agent visibility approval.",
        ]

    codes = {issue["code"] for issue in issues}
    reviews = []
    if "artifact_manifest_not_loader_ready" in codes:
        reviews.append("Resolve artifact manifest readiness first.")
    if (
        "missing_loader_run_record_run_id" in codes
        or "missing_loader_run_record_completed_at" in codes
    ):
        reviews.append("Record loader run ID and completion time.")
    if "missing_loader_run_record_artifact_manifest_path" in codes:
        reviews.append("Record loader run artifact manifest path.")
    if "loader_run_record_manifest_path_mismatch" in codes:
        reviews.append("Resolve loader run record manifest path mismatch.")
    if "invalid_loader_run_entrypoint" in codes:
        reviews.append("Confirm loader run used the artifact-manifest entrypoint.")
    if "loader_run_not_succeeded" in codes:
        reviews.append("Confirm the canonical loader run succeeded.")
    if _has_scope_mismatch(codes):
        reviews.append("Resolve loader run record source, snapshot, or dataset mismatch.")
    if (
        "missing_loader_run_loaded_counts" in codes
        or "invalid_loader_run_loaded_count" in codes
        or "invalid_loader_run_loaded_count_entity_type" in codes
    ):
        reviews.append("Record valid loader run loaded counts.")
    if "loader_run_candidate_count_mismatch" in codes:
        reviews.append("Resolve loader run loaded count mismatch.")
    if not reviews:
        reviews.append("Resolve loader run evidence issues.")
    return reviews


def _has_scope_mismatch(codes: set[str]) -> bool:
    scope_mismatch_codes = {
        "loader_run_record_source_id_mismatch",
        "loader_run_record_snapshot_id_mismatch",
        "loader_run_record_dataset_mismatch",
    }
    return bool(codes & scope_mismatch_codes)


def _non_goals() -> list[str]:
    return [
        "Does not execute the canonical loader.",
        "Does not write database rows.",
        "Does not modify seed data.",
        "Does not refresh RAG or Agent-visible data.",
        "Does not approve Agent/RAG visibility by itself.",
    ]
