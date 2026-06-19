"""No-write review for source usage and citation permissions."""

from typing import Any


ERROR = "error"
ALLOWED_USAGE_STATUSES = {
    "unknown",
    "blocked_pending_authorization",
    "approved_for_internal_review_only",
    "approved_for_real_data_ingestion",
}


def review_source_usage(payload: dict[str, Any]) -> dict[str, Any]:
    """Review whether source usage terms can support real-data ingestion."""
    issues: list[dict[str, Any]] = []
    scope = _dict(payload.get("scope"))
    usage_terms = _dict(payload.get("usage_terms"))
    decision = _dict(payload.get("decision"))

    _check_top_level(payload, issues)
    _check_scope(scope, issues)
    _check_usage_terms(usage_terms, issues)
    _check_decision(decision, issues)
    _require_value(payload, "reviewed_by", issues)
    _require_value(payload, "reviewed_at", issues)

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    return {
        "action": "source_usage_review",
        "passed": ready,
        "ready_for_source_approval_license_review": ready,
        "scope": {
            "source_id": payload.get("source_id"),
            "data_category": scope.get("data_category"),
            "province": scope.get("province"),
            "years": _list(scope.get("years")),
        },
        "evidence_summary": _evidence_summary(payload, usage_terms, decision),
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "non_goals": _non_goals(),
    }


def _check_top_level(
    payload: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if payload.get("action") != "source_usage_review":
        _issue(
            issues,
            "invalid_source_usage_review_action",
            "action must be source_usage_review",
            "action",
        )
    _require_value(payload, "source_id", issues)
    if not payload.get("source_url") and not payload.get("attachment_url"):
        _issue(
            issues,
            "missing_source_usage_url",
            "source_url or attachment_url is required",
            "source_url",
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


def _check_usage_terms(
    usage_terms: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    _require_value(
        usage_terms,
        "copyright_notice",
        issues,
        prefix="usage_terms",
    )
    _require_value(
        usage_terms,
        "citation_or_usage_notes",
        issues,
        prefix="usage_terms",
    )
    if not isinstance(usage_terms.get("redistribution_restriction_detected"), bool):
        _issue(
            issues,
            "missing_usage_terms_redistribution_restriction_detected",
            "usage_terms.redistribution_restriction_detected must be boolean",
            "usage_terms.redistribution_restriction_detected",
        )


def _check_decision(
    decision: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    usage_status = decision.get("usage_status")
    if usage_status not in ALLOWED_USAGE_STATUSES:
        _issue(
            issues,
            "invalid_usage_status",
            "decision.usage_status is invalid",
            "decision.usage_status",
        )
    if decision.get("license_reviewed") is not True:
        _issue(
            issues,
            "source_usage_license_not_reviewed",
            "decision.license_reviewed must be true",
            "decision.license_reviewed",
        )
    if decision.get("allow_real_data_ingestion") is not True:
        _issue(
            issues,
            "source_usage_ingestion_not_allowed",
            "decision.allow_real_data_ingestion must be true",
            "decision.allow_real_data_ingestion",
        )
    if (
        usage_status != "approved_for_real_data_ingestion"
        and decision.get("allow_real_data_ingestion") is True
    ):
        _issue(
            issues,
            "usage_status_does_not_allow_ingestion",
            "usage_status must be approved_for_real_data_ingestion",
            "decision.usage_status",
        )


def _evidence_summary(
    payload: dict[str, Any],
    usage_terms: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "has_source_url": _has_text(payload.get("source_url")),
        "has_attachment_url": _has_text(payload.get("attachment_url")),
        "has_copyright_notice": _has_text(
            usage_terms.get("copyright_notice")
        ),
        "has_citation_or_usage_notes": _has_text(
            usage_terms.get("citation_or_usage_notes")
        ),
        "redistribution_restriction_detected": (
            usage_terms.get("redistribution_restriction_detected")
        ),
        "usage_status": decision.get("usage_status"),
        "license_reviewed": decision.get("license_reviewed") is True,
        "allow_real_data_ingestion": (
            decision.get("allow_real_data_ingestion") is True
        ),
        "has_reviewer": _has_text(payload.get("reviewed_by")),
        "has_reviewed_at": _has_text(payload.get("reviewed_at")),
    }


def _required_reviews(issues: list[dict[str, Any]]) -> list[str]:
    reviews = []
    for issue in issues:
        review = _required_review_for_issue(str(issue.get("code") or ""))
        if review and review not in reviews:
            reviews.append(review)
    return reviews


def _required_review_for_issue(code: str) -> str | None:
    reviews = {
        "invalid_source_usage_review_action": "Use a source_usage_review packet.",
        "missing_source_id": "Provide the reviewed source_id.",
        "missing_source_usage_url": (
            "Provide the official source page URL or attachment URL."
        ),
        "missing_scope_data_category": "Provide the reviewed data category.",
        "missing_scope_province": "Provide the reviewed source province.",
        "missing_scope_years": "Provide reviewed source coverage years.",
        "invalid_scope_year": "Fix invalid reviewed source coverage years.",
        "missing_usage_terms_copyright_notice": (
            "Record official copyright or usage notice."
        ),
        "missing_usage_terms_citation_or_usage_notes": (
            "Record citation or usage notes."
        ),
        "missing_usage_terms_redistribution_restriction_detected": (
            "Record whether redistribution restrictions were detected."
        ),
        "invalid_usage_status": "Choose a valid source usage status.",
        "source_usage_license_not_reviewed": (
            "Complete source license or citation review."
        ),
        "source_usage_ingestion_not_allowed": (
            "Approve real-data ingestion only after usage review passes."
        ),
        "usage_status_does_not_allow_ingestion": (
            "Use approved_for_real_data_ingestion before ingestion approval."
        ),
        "missing_reviewed_by": "Provide usage reviewer identity.",
        "missing_reviewed_at": "Provide usage review date or timestamp.",
    }
    return reviews.get(code)


def _non_goals() -> list[str]:
    return [
        "Does not approve source registry changes.",
        "Does not fetch remote source pages or download attachments.",
        "Does not create raw snapshots.",
        "Does not parse rows or run quality gates.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
