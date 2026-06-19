"""Stdlib-only source registry coverage report."""

from typing import Any

from backend.data_pipeline.sources.smoke import build_source_registry_smoke_review


def build_source_coverage_report(
    payload: dict[str, Any],
    *,
    priority_provinces: list[str] | tuple[str, ...] = (),
    priority_data_categories: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Summarize source registry coverage without importing runtime contracts."""
    smoke_review = build_source_registry_smoke_review(
        payload,
        expected_provinces=priority_provinces,
        expected_data_categories=priority_data_categories,
    )
    sources = payload.get("sources")
    sources = sources if isinstance(sources, list) else []
    valid_sources = [source for source in sources if isinstance(source, dict)]

    province_summary = _build_province_summary(valid_sources)
    data_category_summary = _build_data_category_summary(valid_sources)
    review_status_counts = _review_status_counts(valid_sources)
    issues = list(smoke_review["issues"])
    issues.extend(_coverage_issues(
        province_summary,
        data_category_summary,
        priority_provinces=priority_provinces,
        priority_data_categories=priority_data_categories,
    ))
    issue_counts = _issue_counts(issues)
    gap_summary = _gap_summary(province_summary, priority_provinces)
    readiness = _readiness(gap_summary, issue_counts)

    return {
        "action": "source_coverage_report",
        "passed": issue_counts["error"] == 0,
        "source_count": len(sources),
        "review_status_counts": review_status_counts,
        "priority_scope": {
            "provinces": list(priority_provinces),
            "data_categories": list(priority_data_categories),
        },
        "province_summary": province_summary,
        "data_category_summary": data_category_summary,
        "gap_summary": gap_summary,
        "readiness": readiness,
        "issue_counts": issue_counts,
        "issues": issues,
        "structural_smoke_passed": smoke_review["passed"],
        "non_goals": _non_goals(),
    }


def _build_province_summary(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    province_map: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_id = source.get("source_id")
        source_id = source_id if isinstance(source_id, str) else ""
        coverage = source.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        provinces = [
            province for province in coverage.get("provinces") or []
            if isinstance(province, str)
        ]
        years = [
            year for year in coverage.get("years") or []
            if isinstance(year, int)
        ]
        categories = [
            category for category in source.get("data_categories") or []
            if isinstance(category, str)
        ]
        review_status = source.get("review_status")
        review_status = review_status if isinstance(review_status, str) else "unknown"
        for province in provinces:
            entry = province_map.setdefault(province, {
                "province": province,
                "source_ids": set(),
                "data_categories": set(),
                "years": set(),
                "review_statuses": set(),
                "source_count": 0,
            })
            if source_id:
                entry["source_ids"].add(source_id)
            entry["data_categories"].update(categories)
            entry["years"].update(years)
            entry["review_statuses"].add(review_status)
            entry["source_count"] += 1

    return [
        _freeze_summary_entry(entry)
        for entry in sorted(province_map.values(), key=lambda item: item["province"])
    ]


def _build_data_category_summary(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    category_map: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_id = source.get("source_id")
        source_id = source_id if isinstance(source_id, str) else ""
        coverage = source.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        provinces = [
            province for province in coverage.get("provinces") or []
            if isinstance(province, str)
        ]
        years = [
            year for year in coverage.get("years") or []
            if isinstance(year, int)
        ]
        for category in source.get("data_categories") or []:
            if not isinstance(category, str):
                continue
            entry = category_map.setdefault(category, {
                "data_category": category,
                "source_ids": set(),
                "provinces": set(),
                "years": set(),
                "source_count": 0,
            })
            if source_id:
                entry["source_ids"].add(source_id)
            entry["provinces"].update(provinces)
            entry["years"].update(years)
            entry["source_count"] += 1

    return [
        {
            "data_category": entry["data_category"],
            "source_count": entry["source_count"],
            "source_ids": sorted(entry["source_ids"]),
            "provinces": sorted(entry["provinces"]),
            "years": sorted(entry["years"]),
        }
        for entry in sorted(
            category_map.values(),
            key=lambda item: item["data_category"],
        )
    ]


def _freeze_summary_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "province": entry["province"],
        "source_count": entry["source_count"],
        "source_ids": sorted(entry["source_ids"]),
        "data_categories": sorted(entry["data_categories"]),
        "years": sorted(entry["years"]),
        "review_statuses": sorted(entry["review_statuses"]),
        "has_registered_source": entry["source_count"] > 0,
        "has_registered_year": bool(entry["years"]),
        "has_approved_source": "approved" in entry["review_statuses"],
    }


def _review_status_counts(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in sources:
        status = source.get("review_status")
        status = status if isinstance(status, str) else "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _gap_summary(
    province_summary: list[dict[str, Any]],
    priority_provinces: list[str] | tuple[str, ...],
) -> dict[str, list[str]]:
    province_map = {entry["province"]: entry for entry in province_summary}
    missing_priority = [
        province for province in priority_provinces if province not in province_map
    ]
    priority_without_years = [
        province for province in priority_provinces
        if province in province_map and not province_map[province]["has_registered_year"]
    ]
    priority_without_approved_source = [
        province for province in priority_provinces
        if province in province_map and not province_map[province]["has_approved_source"]
    ]
    return {
        "missing_priority_provinces": missing_priority,
        "priority_provinces_without_years": priority_without_years,
        "priority_provinces_without_approved_source": (
            priority_without_approved_source
        ),
    }


def _readiness(
    gap_summary: dict[str, list[str]],
    issue_counts: dict[str, int],
) -> dict[str, Any]:
    snapshot_blockers = []
    if issue_counts["error"]:
        snapshot_blockers.append("source_registry_errors")
    if gap_summary["missing_priority_provinces"]:
        snapshot_blockers.append("missing_priority_provinces")
    if gap_summary["priority_provinces_without_years"]:
        snapshot_blockers.append("priority_provinces_without_years")
    if gap_summary["priority_provinces_without_approved_source"]:
        snapshot_blockers.append("priority_provinces_without_approved_source")

    return {
        "ready_for_snapshot_planning": not snapshot_blockers,
        "ready_for_loader_discussion": False,
        "ready_for_agent_visibility_discussion": False,
        "snapshot_planning_blockers": snapshot_blockers,
        "loader_discussion_blockers": [
            "requires_source_approval",
            "requires_raw_snapshot",
            "requires_parser_and_quality_gate",
            "requires_loader_approval_packet",
        ],
        "agent_visibility_discussion_blockers": [
            "requires_loader_run_evidence",
            "requires_answer_source_policy_review",
            "requires_agent_visibility_approval",
        ],
    }


def _coverage_issues(
    province_summary: list[dict[str, Any]],
    data_category_summary: list[dict[str, Any]],
    *,
    priority_provinces: list[str] | tuple[str, ...],
    priority_data_categories: list[str] | tuple[str, ...],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    province_map = {entry["province"]: entry for entry in province_summary}
    category_map = {
        entry["data_category"]: entry for entry in data_category_summary
    }

    for province in priority_provinces:
        entry = province_map.get(province)
        if entry is None:
            continue
        if not entry["has_registered_year"]:
            issues.append(_issue(
                "warning",
                "priority_province_without_registered_year",
                f"priority province has no registered dataset year: {province}",
                "province_summary.years",
            ))
        if not entry["has_approved_source"]:
            issues.append(_issue(
                "info",
                "priority_province_without_approved_source",
                f"priority province has no approved source yet: {province}",
                "province_summary.review_statuses",
            ))

    for category in priority_data_categories:
        entry = category_map.get(category)
        if entry is not None and not entry["years"]:
            issues.append(_issue(
                "warning",
                "priority_category_without_registered_year",
                f"priority data category has no registered year: {category}",
                "data_category_summary.years",
            ))

    return issues


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


def _non_goals() -> list[str]:
    return [
        "Does not replace source registry structural smoke review.",
        "Does not approve sources, years, or licenses.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
