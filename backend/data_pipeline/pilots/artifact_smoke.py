"""Stdlib-only smoke review for pilot artifact manifests."""

from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "action",
    "source_id",
    "snapshot_id",
    "dataset",
    "candidate_count",
    "ready_for_loader_execution",
    "artifact_paths",
    "artifact_path_issues",
    "intake_review_issues",
    "artifact_scope_issues",
    "loader_approval_issues",
    "review_summary",
    "loader_handoff",
    "required_reviews",
    "non_goals",
)
READY_ISSUE_FIELDS = (
    "artifact_path_issues",
    "intake_review_issues",
    "artifact_scope_issues",
    "loader_approval_issues",
)


def build_pilot_artifact_smoke_review(
    manifest: dict[str, Any],
    *,
    expected_source_id: str | None = None,
    expected_snapshot_id: str | None = None,
    expected_dataset: str | None = None,
    check_paths: bool = True,
) -> dict[str, Any]:
    """Build a no-dependency smoke review for a pilot artifact manifest."""
    issues: list[dict[str, Any]] = []
    _check_required_fields(manifest, issues)
    _check_basic_shape(manifest, issues)
    _check_expectations(
        manifest,
        issues,
        expected_source_id=expected_source_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_dataset=expected_dataset,
    )
    if check_paths:
        _check_artifact_paths(manifest, issues)
        _check_referenced_artifacts(manifest, issues)

    issue_counts = _issue_counts(issues)
    return {
        "action": "pilot_artifact_manifest_smoke_review",
        "passed": issue_counts["error"] == 0,
        "scope": {
            "source_id": manifest.get("source_id"),
            "snapshot_id": manifest.get("snapshot_id"),
            "dataset": manifest.get("dataset"),
            "candidate_count": manifest.get("candidate_count"),
        },
        "issue_counts": issue_counts,
        "issues": issues,
        "path_summary": _path_summary(manifest),
        "non_goals": [
            "Does not replace the pydantic artifact manifest contract.",
            "Does not run parser or quality gate.",
            "Does not write database rows or seed data.",
            "Does not approve loader execution.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _check_required_fields(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            issues.append(_issue(
                "error",
                f"missing_{field}",
                f"artifact manifest is missing required field: {field}",
                field,
            ))


def _check_basic_shape(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if manifest.get("action") != "real_data_pilot_artifact_manifest":
        issues.append(_issue(
            "error",
            "invalid_action",
            "artifact manifest action is invalid",
            "action",
        ))
    for field in ("source_id", "snapshot_id", "dataset"):
        if not isinstance(manifest.get(field), str) or not manifest.get(field):
            issues.append(_issue(
                "error",
                f"invalid_{field}",
                f"{field} must be a non-empty string",
                field,
            ))
    candidate_count = manifest.get("candidate_count")
    if not isinstance(candidate_count, int) or candidate_count < 0:
        issues.append(_issue(
            "error",
            "invalid_candidate_count",
            "candidate_count must be a non-negative integer",
            "candidate_count",
        ))
    if manifest.get("ready_for_loader_execution") is not True:
        issues.append(_issue(
            "error",
            "manifest_not_loader_ready",
            "ready_for_loader_execution must be true for this smoke",
            "ready_for_loader_execution",
        ))
    for field in READY_ISSUE_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, list):
            issues.append(_issue(
                "error",
                f"invalid_{field}",
                f"{field} must be a list",
                field,
            ))
        elif value:
            issues.append(_issue(
                "error",
                f"non_empty_{field}",
                f"{field} must be empty before loader discussion",
                field,
            ))
    _check_loader_handoff(manifest, issues)


def _check_loader_handoff(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    handoff = manifest.get("loader_handoff")
    if not isinstance(handoff, dict):
        issues.append(_issue(
            "error",
            "invalid_loader_handoff",
            "loader_handoff must be an object",
            "loader_handoff",
        ))
        return
    if handoff.get("recommended_entrypoint") != "load_candidates_after_artifact_manifest":
        issues.append(_issue(
            "error",
            "invalid_loader_handoff_entrypoint",
            "loader_handoff entrypoint is invalid",
            "loader_handoff.recommended_entrypoint",
        ))
    if handoff.get("requires_separate_loader_run_command") is not True:
        issues.append(_issue(
            "error",
            "loader_run_command_not_separate",
            "loader_handoff must require a separate loader run command",
            "loader_handoff.requires_separate_loader_run_command",
        ))


def _check_expectations(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    expected_source_id: str | None,
    expected_snapshot_id: str | None,
    expected_dataset: str | None,
) -> None:
    expectations = {
        "source_id": expected_source_id,
        "snapshot_id": expected_snapshot_id,
        "dataset": expected_dataset,
    }
    for field, expected in expectations.items():
        if expected is not None and manifest.get(field) != expected:
            issues.append(_issue(
                "error",
                f"unexpected_{field}",
                f"{field} does not match expected value",
                field,
            ))


def _check_artifact_paths(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    artifact_paths = manifest.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        issues.append(_issue(
            "error",
            "invalid_artifact_paths",
            "artifact_paths must be an object",
            "artifact_paths",
        ))
        return
    required_file_keys = ("source_audit", "dry_run_audit", "rows_bundle")
    optional_file_keys = ("intake_review", "loader_approval")
    for key in required_file_keys:
        _check_file_path(artifact_paths, key, issues, required=True)
    for key in optional_file_keys:
        _check_file_path(artifact_paths, key, issues, required=False)
    snapshot_dir = artifact_paths.get("snapshot_dir")
    if snapshot_dir is not None and not Path(str(snapshot_dir)).is_dir():
        issues.append(_issue(
            "error",
            "missing_snapshot_dir",
            "artifact_paths.snapshot_dir must exist when provided",
            "artifact_paths.snapshot_dir",
        ))


def _check_referenced_artifacts(
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    artifact_paths = manifest.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        return
    source_audit = _read_artifact(artifact_paths, "source_audit", issues)
    intake_review = _read_artifact(artifact_paths, "intake_review", issues)
    dry_run_audit = _read_artifact(artifact_paths, "dry_run_audit", issues)
    loader_approval = _read_artifact(artifact_paths, "loader_approval", issues)

    if source_audit is not None:
        _check_source_audit_scope(manifest, source_audit, issues)
    if intake_review is not None:
        _check_intake_review_scope(manifest, intake_review, issues)
    if dry_run_audit is not None:
        _check_dry_run_audit_scope(manifest, dry_run_audit, issues)
    if loader_approval is not None:
        _check_loader_approval_scope(manifest, loader_approval, issues)


def _read_artifact(
    artifact_paths: dict[str, Any],
    key: str,
    issues: list[dict[str, Any]],
) -> dict[str, Any] | None:
    value = artifact_paths.get(key)
    if value is None or not Path(str(value)).is_file():
        return None
    try:
        import json

        with Path(str(value)).open(encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        issues.append(_issue(
            "error",
            f"invalid_artifact_json_{key}",
            f"artifact_paths.{key} cannot be read as JSON: {exc}",
            f"artifact_paths.{key}",
        ))
        return None
    if not isinstance(payload, dict):
        issues.append(_issue(
            "error",
            f"invalid_artifact_object_{key}",
            f"artifact_paths.{key} must contain a JSON object",
            f"artifact_paths.{key}",
        ))
        return None
    return payload


def _check_source_audit_scope(
    manifest: dict[str, Any],
    source_audit: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if source_audit.get("passed") is not True:
        issues.append(_issue(
            "error",
            "source_audit_not_passed",
            "source audit must pass before loader discussion",
            "artifact_paths.source_audit.passed",
        ))
    scope = source_audit.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    if scope.get("data_category") != manifest.get("dataset"):
        issues.append(_issue(
            "error",
            "source_audit_dataset_mismatch",
            "source audit data_category must match manifest dataset",
            "artifact_paths.source_audit.scope.data_category",
        ))


def _check_intake_review_scope(
    manifest: dict[str, Any],
    intake_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if intake_review.get("passed") is not True:
        issues.append(_issue(
            "error",
            "intake_review_not_passed",
            "intake review must pass before loader discussion",
            "artifact_paths.intake_review.passed",
        ))
    if intake_review.get("ready_for_snapshot") is not True:
        issues.append(_issue(
            "error",
            "intake_review_not_snapshot_ready",
            "intake review must be snapshot-ready",
            "artifact_paths.intake_review.ready_for_snapshot",
        ))
    scope = intake_review.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    _check_scope_field(
        scope,
        manifest,
        "source_id",
        "artifact_paths.intake_review.scope.source_id",
        "intake_review_source_mismatch",
        issues,
    )
    _check_scope_field(
        scope,
        manifest,
        "dataset",
        "artifact_paths.intake_review.scope.dataset",
        "intake_review_dataset_mismatch",
        issues,
    )


def _check_dry_run_audit_scope(
    manifest: dict[str, Any],
    dry_run_audit: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if dry_run_audit.get("passed") is not True:
        issues.append(_issue(
            "error",
            "dry_run_audit_not_passed",
            "dry-run audit must pass before loader discussion",
            "artifact_paths.dry_run_audit.passed",
        ))
    if dry_run_audit.get("load_ready") is not True:
        issues.append(_issue(
            "error",
            "dry_run_audit_not_load_ready",
            "dry-run audit must be load-ready",
            "artifact_paths.dry_run_audit.load_ready",
        ))
    for field in ("source_id", "snapshot_id", "dataset", "candidate_count"):
        _check_scope_field(
            dry_run_audit,
            manifest,
            field,
            f"artifact_paths.dry_run_audit.{field}",
            f"dry_run_audit_{field}_mismatch",
            issues,
        )


def _check_loader_approval_scope(
    manifest: dict[str, Any],
    loader_approval: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if loader_approval.get("load_allowed") is not True:
        issues.append(_issue(
            "error",
            "loader_approval_not_allowed",
            "loader approval must allow loading before loader discussion",
            "artifact_paths.loader_approval.load_allowed",
        ))
    for field in ("source_id", "snapshot_id", "dataset", "candidate_count"):
        _check_scope_field(
            loader_approval,
            manifest,
            field,
            f"artifact_paths.loader_approval.{field}",
            f"loader_approval_{field}_mismatch",
            issues,
        )


def _check_scope_field(
    artifact: dict[str, Any],
    manifest: dict[str, Any],
    field: str,
    issue_field: str,
    issue_code: str,
    issues: list[dict[str, Any]],
) -> None:
    if artifact.get(field) != manifest.get(field):
        issues.append(_issue(
            "error",
            issue_code,
            f"{field} does not match manifest",
            issue_field,
        ))


def _check_file_path(
    artifact_paths: dict[str, Any],
    key: str,
    issues: list[dict[str, Any]],
    *,
    required: bool,
) -> None:
    value = artifact_paths.get(key)
    if value is None:
        if required:
            issues.append(_issue(
                "error",
                f"missing_artifact_path_{key}",
                f"artifact_paths.{key} is required",
                f"artifact_paths.{key}",
            ))
        return
    if not Path(str(value)).is_file():
        issues.append(_issue(
            "error",
            f"missing_artifact_file_{key}",
            f"artifact_paths.{key} must point to an existing file",
            f"artifact_paths.{key}",
        ))


def _path_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    artifact_paths = manifest.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        return {}
    return {
        key: {
            "path": value,
            "exists": Path(str(value)).exists(),
        }
        for key, value in artifact_paths.items()
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
    return {
        "error": sum(1 for issue in issues if issue["severity"] == "error"),
        "warning": sum(1 for issue in issues if issue["severity"] == "warning"),
        "info": sum(1 for issue in issues if issue["severity"] == "info"),
    }
