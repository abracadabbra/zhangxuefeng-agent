"""No-write review gate for official sample intake packets."""

from typing import Any


ERROR = "error"
WARNING = "warning"


def review_intake_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Review whether an official sample intake packet is ready for snapshot prep."""
    issues: list[dict[str, Any]] = []
    pilot_scope = _dict(payload.get("pilot_scope"))
    source_review = _dict(payload.get("source_review"))
    snapshot_planning_review = _dict(payload.get("snapshot_planning_review"))
    snapshot_review = _dict(payload.get("snapshot_review"))
    quality_config = _dict(payload.get("quality_config"))

    _require_true(
        payload,
        "not_a_dry_run_bundle",
        issues,
        code="not_marked_as_intake_template",
    )
    _check_pilot_scope(pilot_scope, issues)
    _check_source_review(source_review, issues)
    _check_snapshot_planning_review(snapshot_planning_review, pilot_scope, issues)
    _check_snapshot_review(snapshot_review, issues)
    _check_quality_config(pilot_scope, quality_config, issues)

    has_errors = any(issue["severity"] == ERROR for issue in issues)
    return {
        "action": "official_sample_intake_review",
        "passed": not has_errors,
        "ready_for_snapshot": not has_errors,
        "scope": {
            "source_id": pilot_scope.get("source_id"),
            "dataset": pilot_scope.get("dataset"),
            "province": pilot_scope.get("province"),
            "published_year": pilot_scope.get("published_year"),
        },
        "snapshot_planning_review": {
            "ready_for_snapshot_planning": (
                snapshot_planning_review.get("ready_for_snapshot_planning")
            ),
            "source_summary": snapshot_planning_review.get("source_summary"),
        },
        "issue_counts": _count_issues(issues),
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "non_goals": [
            "Does not download remote files.",
            "Does not create raw snapshots.",
            "Does not parse rows.",
            "Does not write databases or seed data.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _check_pilot_scope(scope: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for field in ("source_id", "dataset", "province", "published_year"):
        _require_value(scope, field, issues, code=f"missing_pilot_scope_{field}")
    year = scope.get("published_year")
    if year is not None and not isinstance(year, int):
        _issue(
            issues,
            ERROR,
            "invalid_published_year",
            "pilot_scope.published_year must be an integer",
            field="pilot_scope.published_year",
        )


def _check_source_review(
    source_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if not source_review.get("dataset_page_url") and not source_review.get("attachment_url"):
        _issue(
            issues,
            ERROR,
            "missing_source_url",
            "source_review needs dataset_page_url or attachment_url",
            field="source_review.dataset_page_url",
        )
    _require_true(
        source_review,
        "data_category_confirmed",
        issues,
        code="data_category_not_confirmed",
        prefix="source_review",
    )
    for field in ("license_or_citation_notes", "reviewed_by", "reviewed_at"):
        _require_value(
            source_review,
            field,
            issues,
            code=f"missing_source_review_{field}",
            prefix="source_review",
        )
    review_status = source_review.get("review_status")
    if review_status not in ("reviewed", "approved"):
        _issue(
            issues,
            ERROR,
            "source_review_not_ready",
            "source_review.review_status must be reviewed or approved",
            field="source_review.review_status",
        )


def _check_snapshot_planning_review(
    snapshot_planning_review: dict[str, Any],
    pilot_scope: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if snapshot_planning_review.get("action") != "source_snapshot_planning_review":
        _issue(
            issues,
            ERROR,
            "invalid_snapshot_planning_review_action",
            "snapshot_planning_review.action must be source_snapshot_planning_review",
            field="snapshot_planning_review.action",
        )
    if snapshot_planning_review.get("ready_for_snapshot_planning") is not True:
        _issue(
            issues,
            ERROR,
            "snapshot_planning_not_ready",
            "snapshot planning review must be ready",
            field="snapshot_planning_review.ready_for_snapshot_planning",
        )
    review_scope = _dict(snapshot_planning_review.get("scope"))
    expected = {
        "data_category": pilot_scope.get("dataset"),
        "province": pilot_scope.get("province"),
        "year": pilot_scope.get("published_year"),
    }
    for field, expected_value in expected.items():
        if review_scope.get(field) != expected_value:
            _issue(
                issues,
                ERROR,
                f"snapshot_planning_scope_{field}_mismatch",
                f"snapshot planning scope {field} must match pilot scope",
                field=f"snapshot_planning_review.scope.{field}",
            )
    source_summary = _dict(snapshot_planning_review.get("source_summary"))
    matching_source_ids = _list(source_summary.get("matching_source_ids"))
    source_id = pilot_scope.get("source_id")
    if source_id and source_id not in matching_source_ids:
        _issue(
            issues,
            ERROR,
            "snapshot_planning_source_id_mismatch",
            "snapshot planning source summary must include pilot source_id",
            field="snapshot_planning_review.source_summary.matching_source_ids",
        )


def _check_snapshot_review(
    snapshot_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    required_fields = (
        "snapshot_id",
        "source_url",
        "local_snapshot_dir",
        "original_file_name",
        "original_file_sha256",
        "collected_at",
    )
    for field in required_fields:
        _require_value(
            snapshot_review,
            field,
            issues,
            code=f"missing_snapshot_review_{field}",
            prefix="snapshot_review",
        )
    checksum = snapshot_review.get("original_file_sha256")
    if checksum and not _looks_like_sha256(str(checksum)):
        _issue(
            issues,
            ERROR,
            "invalid_original_file_sha256",
            "snapshot_review.original_file_sha256 must be 64 hex characters",
            field="snapshot_review.original_file_sha256",
        )
    _require_true(
        snapshot_review,
        "published_year_confirmed",
        issues,
        code="published_year_not_confirmed",
        prefix="snapshot_review",
    )
    _require_true(
        snapshot_review,
        "original_file_preserved",
        issues,
        code="original_file_not_preserved",
        prefix="snapshot_review",
    )


def _check_quality_config(
    pilot_scope: dict[str, Any],
    quality_config: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    province = pilot_scope.get("province")
    year = pilot_scope.get("published_year")
    expected_provinces = quality_config.get("expected_provinces")
    expected_years = quality_config.get("expected_years")
    if province and province not in _list(expected_provinces):
        _issue(
            issues,
            ERROR,
            "quality_config_missing_province",
            "quality_config.expected_provinces must include pilot_scope.province",
            field="quality_config.expected_provinces",
        )
    if year and year not in _list(expected_years):
        _issue(
            issues,
            ERROR,
            "quality_config_missing_year",
            "quality_config.expected_years must include pilot_scope.published_year",
            field="quality_config.expected_years",
        )
    _require_true(
        quality_config,
        "require_review_metadata",
        issues,
        code="review_metadata_not_required",
        prefix="quality_config",
    )


def _require_value(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    code: str,
    prefix: str | None = None,
) -> None:
    value = payload.get(field)
    if value is None or value == "":
        qualified = f"{prefix}.{field}" if prefix else field
        _issue(
            issues,
            ERROR,
            code,
            f"{qualified} is required",
            field=qualified,
        )


def _require_true(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    code: str,
    prefix: str | None = None,
    severity: str = ERROR,
) -> None:
    if payload.get(field) is not True:
        qualified = f"{prefix}.{field}" if prefix else field
        _issue(
            issues,
            severity,
            code,
            f"{qualified} must be true",
            field=qualified,
        )


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    *,
    field: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "field": field,
        }
    )


def _count_issues(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {ERROR: 0, WARNING: 0, "info": 0}
    for issue in issues:
        counts[issue["severity"]] += 1
    return counts


def _required_reviews(issues: list[dict[str, Any]]) -> list[str]:
    reviews = []
    for issue in issues:
        review = _required_review_for_issue(str(issue.get("code") or ""))
        if review and review not in reviews:
            reviews.append(review)
    return reviews


def _required_review_for_issue(code: str) -> str | None:
    reviews = {
        "not_marked_as_intake_template": (
            "Mark the packet as an official sample intake packet."
        ),
        "missing_source_url": "Provide dataset page URL or attachment URL.",
        "data_category_not_confirmed": "Confirm the source data category.",
        "source_review_not_ready": "Complete source review before intake.",
        "invalid_snapshot_planning_review_action": (
            "Provide a source snapshot planning review artifact."
        ),
        "snapshot_planning_not_ready": (
            "Resolve source snapshot planning blockers."
        ),
        "snapshot_planning_source_id_mismatch": (
            "Match snapshot planning source summary to pilot source_id."
        ),
        "published_year_not_confirmed": "Confirm the snapshot published year.",
        "original_file_not_preserved": "Confirm the original file is preserved.",
        "invalid_original_file_sha256": "Provide a valid original file checksum.",
        "quality_config_missing_province": (
            "Add the pilot province to quality_config.expected_provinces."
        ),
        "quality_config_missing_year": (
            "Add the pilot year to quality_config.expected_years."
        ),
        "review_metadata_not_required": (
            "Require row review metadata in quality_config."
        ),
    }
    if code.startswith("missing_pilot_scope_"):
        return "Complete the pilot scope."
    if code.startswith("missing_source_review_"):
        return "Complete source review evidence."
    if code.startswith("missing_snapshot_review_"):
        return "Complete snapshot review evidence."
    if code.startswith("snapshot_planning_scope_"):
        return "Match snapshot planning scope to pilot scope."
    return reviews.get(code)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _looks_like_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)
