"""Stdlib-only action queue for the real-data MVP review state."""

from __future__ import annotations

from typing import Any


def build_mvp_action_queue(
    *,
    readiness_summary: dict[str, Any],
    source_review_handoff: dict[str, Any],
) -> dict[str, Any]:
    """Build a human action queue without authorizing data collection."""
    blockers = _str_list(readiness_summary.get("blockers"))
    handoff_state = _object(source_review_handoff.get("current_state"))
    source_actions = _source_review_actions(source_review_handoff)
    snapshot_actions = _snapshot_planning_actions(blockers)
    deferred_actions = _deferred_actions(blockers)
    priority_actions = source_actions + snapshot_actions + deferred_actions
    issue_counts = {
        "error": len([item for item in priority_actions if item["status"] == "blocked"]),
        "warning": len([item for item in priority_actions if item["status"] == "pending"]),
        "info": len([item for item in priority_actions if item["status"] == "deferred"]),
    }
    return {
        "action": "real_data_mvp_action_queue",
        "passed": False,
        "ready_for_human_review": bool(priority_actions),
        "next_gate": _next_gate(source_actions, blockers),
        "scope": {
            "source_id": source_review_handoff.get("source_id"),
            "readiness": _object(readiness_summary.get("scope")),
            "source_review": _object(source_review_handoff.get("scope")),
        },
        "source_review_context": _source_review_context(source_review_handoff),
        "current_state": {
            "ready_for_real_snapshot": (
                readiness_summary.get("ready_for_real_snapshot") is True
            ),
            "source_review_ready": handoff_state.get("source_review_ready") is True,
            "registry_update_ready": handoff_state.get("registry_update_ready") is True,
            "registry_patch_chain_ready": (
                handoff_state.get("registry_patch_chain_ready") is True
            ),
            "usage_to_approval_chain_ready": (
                readiness_summary.get("usage_to_approval_chain_ready") is True
            ),
            "source_to_quality_chain_ready": (
                readiness_summary.get("source_to_quality_chain_ready") is True
            ),
            "evidence_inventory_ready": (
                readiness_summary.get("evidence_inventory_ready") is True
            ),
        },
        "priority_actions": priority_actions,
        "issue_counts": issue_counts,
        "issues": _issues(priority_actions),
        "required_reviews": _required_reviews(
            readiness_summary,
            source_review_handoff,
        ),
        "non_goals": [
            "Does not approve the source.",
            "Does not modify sources.json.",
            "Does not fetch remote source pages or download attachments.",
            "Does not create raw snapshots.",
            "Does not parse rows or run quality gates.",
            "Does not execute loader or write databases.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _source_review_context(source_review_handoff: dict[str, Any]) -> dict[str, Any]:
    actions = [
        item
        for item in source_review_handoff.get("next_manual_actions") or []
        if isinstance(item, dict)
    ]
    return {
        "candidate_url": source_review_handoff.get("candidate_url"),
        "candidate_attachment_url": (
            source_review_handoff.get("candidate_attachment_url")
        ),
        "input_artifacts": _object(source_review_handoff.get("input_artifacts")),
        "verified_action_ids": _action_ids(actions, {"verified", "confirmed"}),
        "pending_action_ids": _action_ids(actions, {"pending"}),
    }


def _source_review_actions(
    source_review_handoff: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = []
    for item in source_review_handoff.get("next_manual_actions") or []:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status in {"verified", "confirmed"}:
            continue
        actions.append({
            "id": item.get("id"),
            "phase": "source_review",
            "status": "pending",
            "instruction": item.get("instruction"),
            "blocks": "source_snapshot_planning",
            "source": "sd_source_review_handoff_blocked.json",
        })
    return actions


def _deferred_actions(blockers: list[str]) -> list[dict[str, Any]]:
    deferred = []
    if "separate_loader_run_command_required" in blockers:
        deferred.append({
            "id": "provide_loader_run_command",
            "phase": "loader",
            "status": "deferred",
            "instruction": (
                "Provide a separate approved loader run command only after "
                "source review and real snapshot planning pass."
            ),
            "blocks": "loader_execution",
            "source": "sd_mvp_readiness_summary.json",
        })
    if "separate_agent_visibility_approval_required" in blockers:
        deferred.append({
            "id": "provide_agent_visibility_approval",
            "phase": "agent_visibility",
            "status": "deferred",
            "instruction": (
                "Provide Agent/RAG visibility approval only after a reviewed "
                "loader run exists."
            ),
            "blocks": "agent_visibility",
            "source": "sd_mvp_readiness_summary.json",
        })
    return deferred


def _snapshot_planning_actions(blockers: list[str]) -> list[dict[str, Any]]:
    if "source_snapshot_planning_not_ready" not in blockers:
        return []
    return [{
        "id": "resolve_source_snapshot_planning",
        "phase": "snapshot_planning",
        "status": "blocked",
        "instruction": "Resolve source review before preparing raw snapshots.",
        "blocks": "raw_snapshot_preparation",
        "source": "sd_mvp_readiness_summary.json",
    }]


def _next_gate(source_actions: list[dict[str, Any]], blockers: list[str]) -> str:
    if source_actions:
        return "source_usage_and_citation_review"
    if "source_snapshot_planning_not_ready" in blockers:
        return "source_snapshot_planning"
    if "separate_loader_run_command_required" in blockers:
        return "loader_run_approval"
    if "separate_agent_visibility_approval_required" in blockers:
        return "agent_visibility_approval"
    return "none"


def _issues(priority_actions: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues = []
    for item in priority_actions:
        status = item.get("status")
        if status not in {"blocked", "pending"}:
            continue
        issues.append({
            "severity": "error" if status == "blocked" else "warning",
            "code": f"{item.get('id')}_{status}",
            "message": str(item.get("instruction") or item.get("id")),
            "field": f"priority_actions.{item.get('id')}",
        })
    return issues


def _required_reviews(*reports: dict[str, Any]) -> list[str]:
    reviews = []
    seen = set()
    for report in reports:
        for item in report.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                reviews.append(item)
    return reviews


def _action_ids(
    actions: list[dict[str, Any]],
    statuses: set[str],
) -> list[str]:
    return [
        str(item.get("id"))
        for item in actions
        if item.get("status") in statuses and item.get("id")
    ]


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
