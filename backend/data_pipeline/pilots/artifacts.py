"""Review manifest helpers for real-data pilot artifacts."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PilotArtifactManifest(BaseModel):
    """Index of review artifacts produced for one real-data pilot run."""

    action: str = "real_data_pilot_artifact_manifest"
    generated_at: datetime
    source_id: str | None = None
    snapshot_id: str | None = None
    dataset: str | None = None
    candidate_count: int | None = None
    ready_for_loader_execution: bool
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    artifact_path_issues: list[str] = Field(default_factory=list)
    intake_review_issues: list[str] = Field(default_factory=list)
    artifact_scope_issues: list[str] = Field(default_factory=list)
    loader_approval_issues: list[str] = Field(default_factory=list)
    review_summary: dict[str, Any] = Field(default_factory=dict)
    loader_handoff: dict[str, Any] = Field(default_factory=dict)
    required_reviews: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)

    def to_review_dict(self) -> dict[str, Any]:
        """Return a stable JSON-ready artifact manifest."""
        return self.model_dump(mode="json")


def build_pilot_artifact_manifest(
    *,
    source_audit: dict[str, Any],
    intake_review: dict[str, Any] | None = None,
    dry_run_audit: dict[str, Any],
    source_audit_path: str,
    intake_review_path: str | None = None,
    dry_run_audit_path: str,
    rows_bundle_path: str,
    snapshot_dir: str | None = None,
    loader_approval: dict[str, Any] | None = None,
    loader_approval_path: str | None = None,
    artifact_path_issues: list[str] | None = None,
    generated_at: datetime | None = None,
) -> PilotArtifactManifest:
    """Build a human-reviewable index for pilot review artifacts."""
    generated = generated_at or datetime.now(timezone.utc)
    artifact_paths = {
        "source_audit": source_audit_path,
        "dry_run_audit": dry_run_audit_path,
        "rows_bundle": rows_bundle_path,
    }
    if intake_review_path is not None:
        artifact_paths["intake_review"] = intake_review_path
    if snapshot_dir is not None:
        artifact_paths["snapshot_dir"] = snapshot_dir
    if loader_approval_path is not None:
        artifact_paths["loader_approval"] = loader_approval_path

    intake_review_issues = _intake_review_issues(intake_review)
    artifact_scope_issues = _artifact_scope_issues(source_audit, dry_run_audit)
    loader_approval_issues = _loader_approval_issues(loader_approval, dry_run_audit)
    ready_for_loader_execution = _is_ready_for_loader_execution(
        source_audit,
        intake_review_issues,
        dry_run_audit,
        loader_approval,
        artifact_path_issues or [],
        artifact_scope_issues,
        loader_approval_issues,
    )

    return PilotArtifactManifest(
        generated_at=generated,
        source_id=_optional_str(dry_run_audit.get("source_id")),
        snapshot_id=_optional_str(dry_run_audit.get("snapshot_id")),
        dataset=_optional_str(dry_run_audit.get("dataset")),
        candidate_count=_optional_int(dry_run_audit.get("candidate_count")),
        ready_for_loader_execution=ready_for_loader_execution,
        artifact_paths=artifact_paths,
        artifact_path_issues=artifact_path_issues or [],
        intake_review_issues=intake_review_issues,
        artifact_scope_issues=artifact_scope_issues,
        loader_approval_issues=loader_approval_issues,
        review_summary=_review_summary(
            source_audit,
            intake_review,
            dry_run_audit,
            loader_approval,
        ),
        loader_handoff=_loader_handoff(ready_for_loader_execution),
        required_reviews=_required_reviews(
            source_audit,
            intake_review,
            intake_review_issues,
            dry_run_audit,
            loader_approval,
            artifact_path_issues or [],
            artifact_scope_issues,
            loader_approval_issues,
            ready_for_loader_execution,
        ),
        non_goals=_non_goals(),
    )


def _is_ready_for_loader_execution(
    source_audit: dict[str, Any],
    intake_review_issues: list[str],
    dry_run_audit: dict[str, Any],
    loader_approval: dict[str, Any] | None,
    artifact_path_issues: list[str],
    artifact_scope_issues: list[str],
    loader_approval_issues: list[str],
) -> bool:
    source_issue_counts = _count_issues_by_severity(source_audit)
    return (
        source_audit.get("passed") is True
        and source_issue_counts["error"] == 0
        and source_issue_counts["warning"] == 0
        and not artifact_path_issues
        and not intake_review_issues
        and not artifact_scope_issues
        and not loader_approval_issues
        and dry_run_audit.get("load_ready") is True
        and dry_run_audit.get("review_status") == "ready_for_loader_review"
        and bool(loader_approval and loader_approval.get("load_allowed") is True)
    )


def _review_summary(
    source_audit: dict[str, Any],
    intake_review: dict[str, Any] | None,
    dry_run_audit: dict[str, Any],
    loader_approval: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "source_audit_scope": dict(source_audit.get("scope") or {}),
        "source_audit_passed": source_audit.get("passed"),
        "source_issue_counts": _count_issues_by_severity(source_audit),
        "intake_review_present": intake_review is not None,
        "intake_review_passed": (
            intake_review.get("passed")
            if intake_review is not None
            else None
        ),
        "intake_ready_for_snapshot": (
            intake_review.get("ready_for_snapshot")
            if intake_review is not None
            else None
        ),
        "intake_issue_counts": _intake_issue_counts(intake_review),
        "intake_scope": dict((intake_review or {}).get("scope") or {}),
        "dry_run_passed": dry_run_audit.get("passed"),
        "dry_run_load_ready": dry_run_audit.get("load_ready"),
        "dry_run_review_status": dry_run_audit.get("review_status"),
        "dry_run_blockers": list(dry_run_audit.get("blockers") or []),
        "dry_run_issue_counts": dict(dry_run_audit.get("issue_counts") or {}),
        "loader_approval_present": loader_approval is not None,
        "loader_load_allowed": (
            loader_approval.get("load_allowed")
            if loader_approval is not None
            else None
        ),
    }


def _loader_handoff(ready_for_loader_execution: bool) -> dict[str, Any]:
    return {
        "recommended_entrypoint": "load_candidates_after_artifact_manifest",
        "artifact_manifest_ready": ready_for_loader_execution,
        "requires_separate_loader_run_command": True,
        "does_not_authorize": [
            "crawler execution",
            "seed data modification",
            "RAG or Agent refresh",
            "production database writes without a separate run command",
        ],
    }


def _required_reviews(
    source_audit: dict[str, Any],
    intake_review: dict[str, Any] | None,
    intake_review_issues: list[str],
    dry_run_audit: dict[str, Any],
    loader_approval: dict[str, Any] | None,
    artifact_path_issues: list[str],
    artifact_scope_issues: list[str],
    loader_approval_issues: list[str],
    ready_for_loader_execution: bool,
) -> list[str]:
    reviews: list[str] = []
    if artifact_path_issues:
        reviews.append("Resolve artifact path issues.")
    if intake_review_issues:
        if intake_review is None:
            reviews.append("Generate and review intake readiness report.")
        else:
            reviews.append("Resolve intake readiness review issues.")
    if artifact_scope_issues:
        reviews.append("Resolve artifact scope issues.")
    if loader_approval_issues:
        reviews.append("Resolve loader approval consistency issues.")
    if source_audit.get("passed") is not True:
        reviews.append("Resolve source registry audit errors.")
    if _count_issues_by_severity(source_audit).get("warning", 0) > 0:
        reviews.append("Review source registry audit warnings.")
    if dry_run_audit.get("load_ready") is not True:
        reviews.append("Resolve dry-run blockers before loader approval.")
    if dry_run_audit.get("review_status") != "ready_for_loader_review":
        reviews.append("Complete dry-run review before loader approval.")
    if loader_approval is None:
        reviews.append("Generate and review loader approval packet.")
    elif loader_approval.get("load_allowed") is not True:
        reviews.append("Resolve loader approval packet before execution.")
    if ready_for_loader_execution:
        reviews.append("Provide a separate approved loader run command.")
    return reviews


def _count_issues_by_severity(audit: dict[str, Any]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in audit.get("issues") or []:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _intake_review_issues(intake_review: dict[str, Any] | None) -> list[str]:
    if intake_review is None:
        return ["missing intake readiness review"]

    issues: list[str] = []
    if intake_review.get("passed") is not True:
        issues.append("intake review did not pass")
    if intake_review.get("ready_for_snapshot") is not True:
        issues.append("intake review is not ready for snapshot")

    issue_counts = _intake_issue_counts(intake_review)
    if issue_counts["error"] > 0:
        issues.append("intake review has error issues")
    if issue_counts["warning"] > 0:
        issues.append("intake review has warning issues")

    return issues


def _intake_issue_counts(intake_review: dict[str, Any] | None) -> dict[str, int]:
    if intake_review is None:
        return {"error": 0, "warning": 0, "info": 0}

    counts = _count_issues_by_severity(intake_review)
    declared = intake_review.get("issue_counts")
    declared = declared if isinstance(declared, dict) else {}
    for severity in counts:
        value = declared.get(severity)
        if isinstance(value, int) and value > counts[severity]:
            counts[severity] = value
    return counts


def _artifact_scope_issues(
    source_audit: dict[str, Any],
    dry_run_audit: dict[str, Any],
) -> list[str]:
    scope = source_audit.get("scope")
    if not isinstance(scope, dict):
        return ["missing source audit scope"]

    issues: list[str] = []
    data_category = scope.get("data_category")
    if data_category and data_category != dry_run_audit.get("dataset"):
        issues.append(
            "source audit data_category does not match dry-run dataset: "
            f"{data_category} != {dry_run_audit.get('dataset')}"
        )

    coverage = dry_run_audit.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    covered_provinces = set((coverage.get("by_province") or {}).keys())
    covered_years = set((coverage.get("by_year") or {}).keys())

    for province in scope.get("expected_provinces") or []:
        if str(province) not in covered_provinces:
            issues.append(
                "source audit province is missing from dry-run coverage: "
                f"{province}"
            )

    for year in scope.get("expected_years") or []:
        if str(year) not in covered_years:
            issues.append(
                "source audit year is missing from dry-run coverage: "
                f"{year}"
            )

    return issues


def _loader_approval_issues(
    loader_approval: dict[str, Any] | None,
    dry_run_audit: dict[str, Any],
) -> list[str]:
    if loader_approval is None:
        return []

    issues: list[str] = []
    for field in ("source_id", "snapshot_id", "dataset", "candidate_count"):
        approval_value = loader_approval.get(field)
        dry_run_value = dry_run_audit.get(field)
        if approval_value != dry_run_value:
            issues.append(
                "loader approval field does not match dry-run audit: "
                f"{field}={approval_value} != {dry_run_value}"
            )

    approval_entity_counts = loader_approval.get("entity_counts")
    dry_run_coverage = dry_run_audit.get("coverage")
    dry_run_coverage = dry_run_coverage if isinstance(dry_run_coverage, dict) else {}
    dry_run_entity_counts = dry_run_coverage.get("by_entity_type")
    if approval_entity_counts != dry_run_entity_counts:
        issues.append(
            "loader approval entity_counts do not match dry-run coverage: "
            f"{approval_entity_counts} != {dry_run_entity_counts}"
        )

    return issues


def _non_goals() -> list[str]:
    return [
        "Does not approve crawler execution.",
        "Does not approve canonical loader execution.",
        "Does not write database rows.",
        "Does not modify seed data.",
        "Does not refresh RAG or Agent-visible data.",
    ]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None
