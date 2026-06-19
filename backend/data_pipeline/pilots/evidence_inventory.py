"""Stdlib-only inventory for real-data evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REQUIRED_ARTIFACTS = (
    "sd_source_snapshot_planning_blocked.json",
    "source_snapshot_planning_approved_example.json",
    "priority_source_coverage_report.json",
    "priority_source_coverage_action_queue.json",
    "priority_source_year_review_coverage_report.json",
    "ha_source_year_review_blocked.json",
    "sd_source_usage_review_blocked.json",
    "source_usage_review_reviewed_example.json",
    "source_usage_to_approval_chain_smoke_reviewed_example.json",
    "sd_source_review_human_checklist_blocked.json",
    "sd_source_review_handoff_blocked.json",
    "sd_source_review_chain_smoke_blocked.json",
    "sd_source_review_approval_candidate_review.json",
    "source_review_chain_smoke_reviewed_example.json",
    "source_review_chain_smoke_reviewed_example_update_plan.json",
    "source_registry_patch_approval_reviewed_example_review.json",
    "source_registry_patch_preview_reviewed_example.json",
    "source_registry_patch_chain_smoke_reviewed_example.json",
    "sd_source_registry_update_plan_blocked.json",
    "sd_source_registry_patch_approval_blocked.json",
    "sd_source_registry_patch_preview_blocked.json",
    "sd_source_registry_patch_chain_smoke_blocked.json",
    "source_to_intake_chain_smoke_approved_example.json",
    "source_intake_review_approved_example.json",
    "source_parser_rows_bundle_smoke_approved_example.json",
    "source_quality_smoke_approved_example.json",
    "source_to_quality_chain_smoke_approved_example.json",
    "sd_intake_review.json",
    "sd_parser_rows_bundle_smoke.json",
    "sd_quality_smoke.json",
    "sd_pilot_artifact_manifest.json",
    "sd_answer_source_policy.json",
    "sd_agent_visibility_activation_review.json",
    "sd_loader_run_evidence_templates_blocked.json",
    "sd_example_chain_smoke.json",
    "sd_example_chain_smoke_templates_blocked.json",
    "source_review_approval_reviewed_example_review.json",
    "source_review_approval_reviewed_example_update_plan_blocked.json",
    "sd_mvp_readiness_summary.json",
    "sd_mvp_action_queue.json",
)


def build_evidence_artifact_inventory(
    artifacts_dir: str | Path,
    *,
    required_artifacts: Iterable[str] | None = DEFAULT_REQUIRED_ARTIFACTS,
    exclude_required_reviews_from: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build a no-write inventory for checked evidence artifact JSON files."""
    artifacts_path = Path(artifacts_dir)
    issues: list[dict[str, Any]] = []
    required_names = tuple(required_artifacts or ())
    excluded_review_names = set(exclude_required_reviews_from or ())
    artifact_records: list[dict[str, Any]] = []

    if not artifacts_path.is_dir():
        issues.append(_issue(
            "error",
            "missing_artifacts_dir",
            "artifacts directory does not exist",
            "artifacts_dir",
        ))
        artifact_files: list[Path] = []
    else:
        artifact_files = sorted(artifacts_path.glob("*.json"))

    existing_names = {path.name for path in artifact_files}
    for name in required_names:
        if name not in existing_names:
            issues.append(_issue(
                "error",
                "missing_required_artifact",
                f"required evidence artifact is missing: {name}",
                f"artifacts.{name}",
            ))

    for path in artifact_files:
        artifact_records.append(_artifact_record(path, issues))

    issue_counts = _issue_counts(issues)
    return {
        "action": "real_data_evidence_artifact_inventory",
        "passed": issue_counts["error"] == 0,
        "artifacts_dir": str(artifacts_path),
        "artifact_count": len(artifact_records),
        "required_artifacts": list(required_names),
        "artifacts": artifact_records,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _collect_required_reviews(
            artifact_records,
            excluded_names=excluded_review_names,
        ),
        "non_goals": [
            "Does not fetch remote data.",
            "Does not create raw snapshots.",
            "Does not parse rows or run quality gates.",
            "Does not write database rows or seed data.",
            "Does not approve loader execution.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _artifact_record(
    path: Path,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "valid_json": False,
        "json_object": False,
        "action": None,
        "passed": None,
        "ready_fields": {},
        "issue_counts": None,
        "required_review_count": 0,
        "non_goal_count": 0,
    }
    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(_issue(
            "error",
            "invalid_artifact_json",
            f"artifact JSON cannot be read: {exc}",
            f"artifacts.{path.name}",
        ))
        return record

    record["valid_json"] = True
    if not isinstance(payload, dict):
        issues.append(_issue(
            "error",
            "artifact_not_object",
            "artifact JSON must be an object",
            f"artifacts.{path.name}",
        ))
        return record

    record["json_object"] = True
    record["action"] = payload.get("action")
    record["passed"] = payload.get("passed")
    record["ready_fields"] = _ready_fields(payload)
    record["issue_counts"] = payload.get("issue_counts")
    record["required_review_count"] = _list_len(payload.get("required_reviews"))
    record["non_goal_count"] = _list_len(payload.get("non_goals"))
    if not record["action"]:
        issues.append(_issue(
            "warning",
            "artifact_missing_action",
            "artifact has no action field",
            f"artifacts.{path.name}.action",
        ))
    return record


def _ready_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in sorted(payload)
        if key.startswith("ready_") or key.startswith("ready_for_")
    }


def _collect_required_reviews(
    artifact_records: list[dict[str, Any]],
    *,
    excluded_names: set[str],
) -> list[str]:
    reviews: list[str] = []
    seen: set[str] = set()
    for record in artifact_records:
        path = Path(str(record["path"]))
        if path.name in excluded_names:
            continue
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        for item in payload.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                reviews.append(item)
    return reviews


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


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
