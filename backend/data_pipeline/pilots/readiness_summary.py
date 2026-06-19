"""Stdlib-only MVP readiness summary for real-data evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.pilots.evidence_inventory import (
    build_evidence_artifact_inventory,
)


def build_mvp_readiness_summary(
    *,
    source_snapshot_planning_review: dict[str, Any],
    example_chain_smoke: dict[str, Any],
    evidence_inventory: dict[str, Any],
    source_to_quality_chain_smoke: dict[str, Any] | None = None,
    usage_to_approval_chain_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize current MVP readiness without authorizing any real data action."""
    source_ready = (
        source_snapshot_planning_review.get("passed") is True
        and source_snapshot_planning_review.get("ready_for_snapshot_planning") is True
    )
    synthetic_chain_ready = example_chain_smoke.get("passed") is True
    source_to_quality_ready = _optional_passed(source_to_quality_chain_smoke)
    usage_to_approval_ready = _optional_passed(usage_to_approval_chain_smoke)
    inventory_ready = evidence_inventory.get("passed") is True
    loader_reviews = _chain_requires_review(
        example_chain_smoke,
        "loader run command",
    )
    agent_reviews = _chain_requires_review(
        example_chain_smoke,
        "Agent visibility approval",
    )
    blockers = _blockers(
        source_ready=source_ready,
        synthetic_chain_ready=synthetic_chain_ready,
        source_to_quality_ready=source_to_quality_ready,
        usage_to_approval_ready=usage_to_approval_ready,
        inventory_ready=inventory_ready,
        loader_reviews=loader_reviews,
        agent_reviews=agent_reviews,
    )
    return {
        "action": "real_data_mvp_readiness_summary",
        "passed": not blockers,
        "ready_for_real_snapshot": source_ready,
        "synthetic_chain_ready": synthetic_chain_ready,
        "usage_to_approval_chain_ready": usage_to_approval_ready,
        "source_to_quality_chain_ready": source_to_quality_ready,
        "evidence_inventory_ready": inventory_ready,
        "ready_for_loader_discussion": (
            source_ready
            and synthetic_chain_ready
            and usage_to_approval_ready is not False
            and source_to_quality_ready is not False
            and inventory_ready
            and not loader_reviews
        ),
        "ready_for_agent_visibility_discussion": (
            source_ready
            and synthetic_chain_ready
            and usage_to_approval_ready is not False
            and source_to_quality_ready is not False
            and inventory_ready
            and not loader_reviews
            and not agent_reviews
        ),
        "scope": _scope(
            source_snapshot_planning_review,
            example_chain_smoke,
            source_to_quality_chain_smoke,
            usage_to_approval_chain_smoke,
        ),
        "source_summary": source_snapshot_planning_review.get("source_summary"),
        "artifact_summary": {
            "artifact_count": evidence_inventory.get("artifact_count"),
            "issue_counts": evidence_inventory.get("issue_counts"),
        },
        "blockers": blockers,
        "required_reviews": _required_reviews(
            source_snapshot_planning_review,
            example_chain_smoke,
            source_to_quality_chain_smoke,
            usage_to_approval_chain_smoke,
            evidence_inventory,
        ),
        "non_goals": [
            "Does not approve source review.",
            "Does not fetch remote data or download official attachments.",
            "Does not create raw snapshots.",
            "Does not execute parser, quality gate, or canonical loader.",
            "Does not write database rows, seed data, RAG indexes, or Agent data.",
            "Does not replace separate loader or Agent visibility approvals.",
        ],
    }


def build_mvp_readiness_summary_from_paths(
    *,
    source_snapshot_planning_review_path: str | Path,
    example_chain_smoke_path: str | Path,
    artifacts_dir: str | Path,
    source_to_quality_chain_smoke_path: str | Path | None = None,
    usage_to_approval_chain_smoke_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load checked evidence files and build the no-write readiness summary."""
    source_review = _load_json_object(source_snapshot_planning_review_path)
    chain_smoke = _load_json_object(example_chain_smoke_path)
    source_to_quality = _load_optional_source_to_quality(
        artifacts_dir,
        source_to_quality_chain_smoke_path,
    )
    usage_to_approval = _load_optional_usage_to_approval(
        artifacts_dir,
        usage_to_approval_chain_smoke_path,
    )
    inventory = build_evidence_artifact_inventory(
        artifacts_dir,
        exclude_required_reviews_from=("sd_mvp_readiness_summary.json",),
    )
    return build_mvp_readiness_summary(
        source_snapshot_planning_review=source_review,
        example_chain_smoke=chain_smoke,
        source_to_quality_chain_smoke=source_to_quality,
        usage_to_approval_chain_smoke=usage_to_approval,
        evidence_inventory=inventory,
    )


def _load_json_object(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _load_optional_source_to_quality(
    artifacts_dir: str | Path,
    source_to_quality_chain_smoke_path: str | Path | None,
) -> dict[str, Any] | None:
    path = (
        Path(source_to_quality_chain_smoke_path)
        if source_to_quality_chain_smoke_path is not None
        else Path(artifacts_dir) / "source_to_quality_chain_smoke_approved_example.json"
    )
    if not path.is_file():
        return None
    return _load_json_object(path)


def _load_optional_usage_to_approval(
    artifacts_dir: str | Path,
    usage_to_approval_chain_smoke_path: str | Path | None,
) -> dict[str, Any] | None:
    path = (
        Path(usage_to_approval_chain_smoke_path)
        if usage_to_approval_chain_smoke_path is not None
        else (
            Path(artifacts_dir)
            / "source_usage_to_approval_chain_smoke_reviewed_example.json"
        )
    )
    if not path.is_file():
        return None
    return _load_json_object(path)


def _optional_passed(report: dict[str, Any] | None) -> bool | None:
    if report is None:
        return None
    return report.get("passed") is True


def _chain_requires_review(report: dict[str, Any], text: str) -> bool:
    return any(
        text in item
        for item in report.get("required_reviews") or []
        if isinstance(item, str)
    )


def _blockers(
    *,
    source_ready: bool,
    synthetic_chain_ready: bool,
    source_to_quality_ready: bool | None,
    usage_to_approval_ready: bool | None,
    inventory_ready: bool,
    loader_reviews: bool,
    agent_reviews: bool,
) -> list[str]:
    blockers = []
    if not source_ready:
        blockers.append("source_snapshot_planning_not_ready")
    if not synthetic_chain_ready:
        blockers.append("synthetic_example_chain_not_ready")
    if usage_to_approval_ready is False:
        blockers.append("usage_to_approval_chain_not_ready")
    if source_to_quality_ready is False:
        blockers.append("source_to_quality_chain_not_ready")
    if not inventory_ready:
        blockers.append("evidence_inventory_not_ready")
    if loader_reviews:
        blockers.append("separate_loader_run_command_required")
    if agent_reviews:
        blockers.append("separate_agent_visibility_approval_required")
    return blockers


def _scope(
    source_snapshot_planning_review: dict[str, Any],
    example_chain_smoke: dict[str, Any],
    source_to_quality_chain_smoke: dict[str, Any] | None,
    usage_to_approval_chain_smoke: dict[str, Any] | None,
) -> dict[str, Any]:
    source_scope = source_snapshot_planning_review.get("scope")
    chain_scope = example_chain_smoke.get("scope")
    quality_chain_scope = (
        source_to_quality_chain_smoke.get("scope")
        if isinstance(source_to_quality_chain_smoke, dict)
        else None
    )
    usage_chain_scope = (
        usage_to_approval_chain_smoke.get("scope")
        if isinstance(usage_to_approval_chain_smoke, dict)
        else None
    )
    return {
        "source_snapshot_planning": source_scope if isinstance(source_scope, dict) else {},
        "synthetic_example_chain": chain_scope if isinstance(chain_scope, dict) else {},
        "usage_to_approval_chain": (
            usage_chain_scope if isinstance(usage_chain_scope, dict) else {}
        ),
        "source_to_quality_chain": (
            quality_chain_scope if isinstance(quality_chain_scope, dict) else {}
        ),
    }


def _required_reviews(*reports: dict[str, Any] | None) -> list[str]:
    reviews = []
    seen = set()
    for report in reports:
        if report is None:
            continue
        for item in report.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                reviews.append(item)
    return reviews
