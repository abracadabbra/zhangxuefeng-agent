"""No-write review for source approval packets."""

from typing import Any


ERROR = "error"


def review_source_approval(payload: dict[str, Any]) -> dict[str, Any]:
    """Review whether a source approval packet can update registry metadata."""
    issues: list[dict[str, Any]] = []
    scope = _dict(payload.get("scope"))
    evidence = _dict(payload.get("evidence"))
    usage_review = _dict(payload.get("usage_review"))

    _check_top_level(payload, issues)
    _check_scope(scope, issues)
    _check_evidence(evidence, issues)
    _check_usage_review(payload, scope, usage_review, issues)
    _require_value(payload, "reviewed_by", issues)
    _require_value(payload, "reviewed_at", issues)

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    return {
        "action": "source_review_approval_review",
        "passed": ready,
        "ready_for_registry_update": ready,
        "scope": {
            "source_id": payload.get("source_id"),
            "target_review_status": payload.get("target_review_status"),
            "data_category": scope.get("data_category"),
            "province": scope.get("province"),
            "years": _list(scope.get("years")),
        },
        "evidence_summary": _evidence_summary(payload, evidence, usage_review),
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "registry_update_hint": _registry_update_hint(payload, scope, ready),
        "non_goals": _non_goals(),
    }


def _check_top_level(
    payload: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if payload.get("action") != "source_review_approval":
        _issue(
            issues,
            "invalid_source_review_approval_action",
            "action must be source_review_approval",
            "action",
        )
    if payload.get("allow_source_review_approval") is not True:
        _issue(
            issues,
            "source_review_approval_not_allowed",
            "allow_source_review_approval must be true",
            "allow_source_review_approval",
        )
    _require_value(payload, "source_id", issues)
    if payload.get("target_review_status") != "approved":
        _issue(
            issues,
            "source_review_status_not_approved",
            "target_review_status must be approved",
            "target_review_status",
        )


def _check_scope(scope: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for field in ("data_category", "province"):
        _require_value(scope, field, issues, prefix="scope")
    years = scope.get("years")
    if not isinstance(years, list) or not years:
        _issue(
            issues,
            "missing_scope_years",
            "scope.years must be a non-empty list",
            "scope.years",
        )
        return
    invalid_years = [
        year for year in years if not isinstance(year, int) or year < 2000
    ]
    if invalid_years:
        _issue(
            issues,
            "invalid_scope_year",
            f"scope.years contains invalid values: {invalid_years}",
            "scope.years",
        )


def _check_evidence(
    evidence: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if not evidence.get("dataset_page_url") and not evidence.get("attachment_url"):
        _issue(
            issues,
            "missing_source_evidence_url",
            "evidence needs dataset_page_url or attachment_url",
            "evidence.dataset_page_url",
        )
    _require_value(
        evidence,
        "license_or_citation_notes",
        issues,
        prefix="evidence",
    )
    _require_true(
        evidence,
        "data_category_confirmed",
        issues,
        prefix="evidence",
    )
    _require_true(
        evidence,
        "published_year_confirmed",
        issues,
        prefix="evidence",
    )
    _require_true(evidence, "license_reviewed", issues, prefix="evidence")


def _check_usage_review(
    payload: dict[str, Any],
    scope: dict[str, Any],
    usage_review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if not usage_review:
        _issue(
            issues,
            "missing_source_usage_review",
            "usage_review is required before source approval",
            "usage_review",
        )
        return
    if usage_review.get("action") != "source_usage_review":
        _issue(
            issues,
            "invalid_source_usage_review",
            "usage_review.action must be source_usage_review",
            "usage_review.action",
        )
    if usage_review.get("ready_for_source_approval_license_review") is not True:
        _issue(
            issues,
            "source_usage_review_not_ready",
            "usage review must be ready for source approval",
            "usage_review.ready_for_source_approval_license_review",
        )
    usage_scope = _dict(usage_review.get("scope"))
    _check_usage_scope(payload, scope, usage_scope, issues)


def _check_usage_scope(
    payload: dict[str, Any],
    scope: dict[str, Any],
    usage_scope: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    expected = {
        "source_id": payload.get("source_id"),
        "data_category": scope.get("data_category"),
        "province": scope.get("province"),
        "years": _list(scope.get("years")),
    }
    actual = {
        "source_id": usage_scope.get("source_id"),
        "data_category": usage_scope.get("data_category"),
        "province": usage_scope.get("province"),
        "years": _list(usage_scope.get("years")),
    }
    if actual != expected:
        _issue(
            issues,
            "source_usage_review_scope_mismatch",
            "usage review scope must match source approval scope",
            "usage_review.scope",
        )


def _registry_update_hint(
    payload: dict[str, Any],
    scope: dict[str, Any],
    ready: bool,
) -> dict[str, Any]:
    return {
        "can_update_registry": ready,
        "source_id": payload.get("source_id"),
        "target_review_status": payload.get("target_review_status"),
        "add_data_category_if_missing": scope.get("data_category"),
        "add_province_if_missing": scope.get("province"),
        "add_years_if_missing": _list(scope.get("years")),
    }


def _evidence_summary(
    payload: dict[str, Any],
    evidence: dict[str, Any],
    usage_review: dict[str, Any],
) -> dict[str, bool]:
    """Summarize review evidence presence without changing gate decisions."""
    has_dataset_page_url = _has_text(evidence.get("dataset_page_url"))
    has_attachment_url = _has_text(evidence.get("attachment_url"))
    has_source_url = (
        _has_text(evidence.get("source_url"))
        or has_dataset_page_url
        or has_attachment_url
    )
    return {
        "has_dataset_page_url": has_dataset_page_url,
        "has_attachment_url": has_attachment_url,
        "has_source_url": has_source_url,
        "has_license_or_citation_notes": _has_text(
            evidence.get("license_or_citation_notes")
        ),
        "data_category_confirmed": evidence.get("data_category_confirmed")
        is True,
        "published_year_confirmed": evidence.get("published_year_confirmed")
        is True,
        "license_reviewed": evidence.get("license_reviewed") is True,
        "has_usage_review": bool(usage_review),
        "usage_review_ready": (
            usage_review.get("ready_for_source_approval_license_review") is True
        ),
        "has_reviewer": _has_text(payload.get("reviewed_by")),
        "has_reviewed_at": _has_text(payload.get("reviewed_at")),
    }


def _require_value(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    prefix: str | None = None,
) -> None:
    value = payload.get(field)
    if value is None or value == "":
        qualified = f"{prefix}.{field}" if prefix else field
        _issue(
            issues,
            f"missing_{qualified.replace('.', '_')}",
            f"{qualified} is required",
            qualified,
        )


def _require_true(
    payload: dict[str, Any],
    field: str,
    issues: list[dict[str, Any]],
    *,
    prefix: str,
) -> None:
    if payload.get(field) is not True:
        qualified = f"{prefix}.{field}"
        _issue(
            issues,
            f"{qualified.replace('.', '_')}_not_confirmed",
            f"{qualified} must be true",
            qualified,
        )


def _issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    field: str,
) -> None:
    issues.append({
        "severity": ERROR,
        "code": code,
        "message": message,
        "field": field,
    })


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {ERROR: 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
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
        "invalid_source_review_approval_action": (
            "Use a source_review_approval packet."
        ),
        "source_review_approval_not_allowed": (
            "Set allow_source_review_approval=true only after human review."
        ),
        "missing_source_id": "Provide the reviewed source_id.",
        "source_review_status_not_approved": (
            "Set target_review_status=approved for a registry approval."
        ),
        "missing_scope_data_category": (
            "Provide the reviewed source data category."
        ),
        "missing_scope_province": "Provide the reviewed source province.",
        "missing_scope_years": "Provide reviewed source coverage years.",
        "invalid_scope_year": "Fix invalid reviewed source coverage years.",
        "missing_source_evidence_url": (
            "Provide an official dataset page URL or attachment URL."
        ),
        "missing_evidence_license_or_citation_notes": (
            "Provide source license or citation notes."
        ),
        "evidence_data_category_confirmed_not_confirmed": (
            "Confirm the official dataset category."
        ),
        "evidence_published_year_confirmed_not_confirmed": (
            "Confirm the official dataset published year."
        ),
        "evidence_license_reviewed_not_confirmed": (
            "Complete license or citation review."
        ),
        "missing_source_usage_review": (
            "Attach a source usage review before source approval."
        ),
        "invalid_source_usage_review": "Attach a valid source_usage_review.",
        "source_usage_review_not_ready": (
            "Complete source usage review before source approval."
        ),
        "source_usage_review_scope_mismatch": (
            "Align source usage review scope with source approval scope."
        ),
        "missing_reviewed_by": "Provide reviewer identity.",
        "missing_reviewed_at": "Provide review date or timestamp.",
    }
    return reviews.get(code)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _non_goals() -> list[str]:
    return [
        "Does not modify the source registry.",
        "Does not fetch remote source pages.",
        "Does not create raw snapshots.",
        "Does not parse rows or run quality gates.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
