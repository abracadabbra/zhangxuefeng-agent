"""No-write review for official dataset year registration."""

from __future__ import annotations

from typing import Any


ERROR = "error"


def review_source_years(payload: dict[str, Any]) -> dict[str, Any]:
    """Review whether official dataset years can be registered for a source."""
    issues: list[dict[str, Any]] = []
    scope = _dict(payload.get("scope"))
    evidence = _list_of_dicts(payload.get("year_evidence"))
    decision = _dict(payload.get("decision"))

    _check_top_level(payload, issues)
    _check_scope(scope, issues)
    _check_candidate_years(payload, issues)
    _check_year_evidence(payload, scope, evidence, issues)
    _check_decision(payload, decision, issues)
    _require_value(payload, "reviewed_by", issues)
    _require_value(payload, "reviewed_at", issues)

    issue_counts = _issue_counts(issues)
    ready = issue_counts[ERROR] == 0
    return {
        "action": "source_year_review",
        "passed": ready,
        "ready_for_source_year_registration": ready,
        "scope": {
            "source_id": payload.get("source_id"),
            "province": scope.get("province"),
            "data_categories": _str_list(scope.get("data_categories")),
            "candidate_years": _int_list(payload.get("candidate_years")),
        },
        "evidence_summary": _evidence_summary(payload, evidence, decision),
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "registry_update_hint": _registry_update_hint(payload, decision, ready),
        "non_goals": _non_goals(),
    }


def _check_top_level(
    payload: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if payload.get("action") != "source_year_review":
        _issue(
            issues,
            "invalid_source_year_review_action",
            "action must be source_year_review",
            "action",
        )
    _require_value(payload, "source_id", issues)
    if not payload.get("source_url") and not payload.get("homepage_url"):
        _issue(
            issues,
            "missing_source_year_review_url",
            "source_url or homepage_url is required",
            "source_url",
        )


def _check_scope(scope: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    _require_value(scope, "province", issues, prefix="scope")
    categories = scope.get("data_categories")
    if not isinstance(categories, list) or not _str_list(categories):
        _issue(
            issues,
            "missing_scope_data_categories",
            "scope.data_categories must be a non-empty list",
            "scope.data_categories",
        )


def _check_candidate_years(
    payload: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    years = payload.get("candidate_years")
    if not isinstance(years, list) or not years:
        _issue(
            issues,
            "missing_candidate_years",
            "candidate_years must be a non-empty list",
            "candidate_years",
        )
        return
    invalid_years = [
        year for year in years if not isinstance(year, int) or year < 2000
    ]
    if invalid_years:
        _issue(
            issues,
            "invalid_candidate_year",
            f"candidate_years contains invalid values: {invalid_years}",
            "candidate_years",
        )


def _check_year_evidence(
    payload: dict[str, Any],
    scope: dict[str, Any],
    evidence: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    if not evidence:
        _issue(
            issues,
            "missing_year_evidence",
            "year_evidence is required for candidate years",
            "year_evidence",
        )
        return

    candidate_years = set(_int_list(payload.get("candidate_years")))
    evidence_years = set()
    for index, item in enumerate(evidence):
        field_prefix = f"year_evidence.{index}"
        year = item.get("year")
        if not isinstance(year, int) or year < 2000:
            _issue(
                issues,
                "invalid_year_evidence_year",
                "year_evidence.year must be an integer >= 2000",
                f"{field_prefix}.year",
            )
            continue
        evidence_years.add(year)
        if not item.get("dataset_page_url") and not item.get("attachment_url"):
            _issue(
                issues,
                "missing_year_evidence_url",
                "year evidence needs dataset_page_url or attachment_url",
                f"{field_prefix}.dataset_page_url",
            )
        if item.get("published_year_confirmed") is not True:
            _issue(
                issues,
                "year_evidence_published_year_not_confirmed",
                "year evidence published year must be confirmed",
                f"{field_prefix}.published_year_confirmed",
            )
        if item.get("source_matches_scope") is not True:
            _issue(
                issues,
                "year_evidence_scope_not_confirmed",
                "year evidence must match reviewed source scope",
                f"{field_prefix}.source_matches_scope",
            )
        _check_evidence_categories(scope, item, field_prefix, issues)

    missing_evidence_years = sorted(candidate_years - evidence_years)
    if missing_evidence_years:
        _issue(
            issues,
            "missing_candidate_year_evidence",
            f"candidate years missing evidence: {missing_evidence_years}",
            "year_evidence",
        )


def _check_evidence_categories(
    scope: dict[str, Any],
    evidence: dict[str, Any],
    field_prefix: str,
    issues: list[dict[str, Any]],
) -> None:
    scope_categories = set(_str_list(scope.get("data_categories")))
    evidence_categories = set(_str_list(evidence.get("data_categories")))
    if not evidence_categories:
        _issue(
            issues,
            "missing_year_evidence_data_categories",
            "year evidence data_categories must be non-empty",
            f"{field_prefix}.data_categories",
        )
        return
    missing_categories = sorted(scope_categories - evidence_categories)
    if missing_categories:
        _issue(
            issues,
            "year_evidence_category_mismatch",
            f"year evidence misses scope categories: {missing_categories}",
            f"{field_prefix}.data_categories",
        )


def _check_decision(
    payload: dict[str, Any],
    decision: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    if decision.get("allow_source_year_registration") is not True:
        _issue(
            issues,
            "source_year_registration_not_allowed",
            "decision.allow_source_year_registration must be true",
            "decision.allow_source_year_registration",
        )
    register_years = decision.get("register_years")
    if not isinstance(register_years, list) or not register_years:
        _issue(
            issues,
            "missing_register_years",
            "decision.register_years must be a non-empty list",
            "decision.register_years",
        )
        return
    invalid_years = [
        year for year in register_years if not isinstance(year, int) or year < 2000
    ]
    if invalid_years:
        _issue(
            issues,
            "invalid_register_year",
            f"decision.register_years contains invalid values: {invalid_years}",
            "decision.register_years",
        )
    candidate_years = set(_int_list(payload.get("candidate_years")))
    extra_years = sorted(set(_int_list(register_years)) - candidate_years)
    if extra_years:
        _issue(
            issues,
            "register_years_not_in_candidates",
            f"register_years are not in candidate_years: {extra_years}",
            "decision.register_years",
        )


def _evidence_summary(
    payload: dict[str, Any],
    evidence: list[dict[str, Any]],
    decision: dict[str, Any],
) -> dict[str, Any]:
    candidate_years = set(_int_list(payload.get("candidate_years")))
    return {
        "has_source_url": _has_text(payload.get("source_url")),
        "has_homepage_url": _has_text(payload.get("homepage_url")),
        "candidate_year_count": len(_int_list(payload.get("candidate_years"))),
        "year_evidence_count": len(evidence),
        "all_candidate_years_have_evidence": (
            bool(candidate_years)
            and candidate_years <= {item.get("year") for item in evidence}
        ),
        "allow_source_year_registration": (
            decision.get("allow_source_year_registration") is True
        ),
        "register_years": _int_list(decision.get("register_years")),
        "has_reviewer": _has_text(payload.get("reviewed_by")),
        "has_reviewed_at": _has_text(payload.get("reviewed_at")),
    }


def _registry_update_hint(
    payload: dict[str, Any],
    decision: dict[str, Any],
    ready: bool,
) -> dict[str, Any]:
    return {
        "can_update_registry_years": ready,
        "source_id": payload.get("source_id"),
        "add_years_if_missing": _int_list(decision.get("register_years")),
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
        "invalid_source_year_review_action": "Use a source_year_review packet.",
        "missing_source_id": "Provide the reviewed source_id.",
        "missing_source_year_review_url": (
            "Provide the official source or homepage URL."
        ),
        "missing_scope_province": "Provide the reviewed source province.",
        "missing_scope_data_categories": (
            "Provide reviewed source data categories."
        ),
        "missing_candidate_years": "Review official dataset candidate years.",
        "invalid_candidate_year": "Fix invalid candidate dataset years.",
        "missing_year_evidence": (
            "Attach official evidence for each candidate dataset year."
        ),
        "invalid_year_evidence_year": "Fix invalid year evidence years.",
        "missing_year_evidence_url": (
            "Provide official dataset page or attachment evidence."
        ),
        "year_evidence_published_year_not_confirmed": (
            "Confirm each official dataset published year."
        ),
        "year_evidence_scope_not_confirmed": (
            "Confirm year evidence matches the reviewed source scope."
        ),
        "missing_year_evidence_data_categories": (
            "Record data categories for each year evidence item."
        ),
        "year_evidence_category_mismatch": (
            "Align year evidence categories with reviewed scope."
        ),
        "missing_candidate_year_evidence": (
            "Attach evidence for every candidate year."
        ),
        "source_year_registration_not_allowed": (
            "Allow source year registration only after human review passes."
        ),
        "missing_register_years": "Choose reviewed years to register.",
        "invalid_register_year": "Fix invalid years selected for registration.",
        "register_years_not_in_candidates": (
            "Register only reviewed candidate years."
        ),
        "missing_reviewed_by": "Provide year reviewer identity.",
        "missing_reviewed_at": "Provide year review date or timestamp.",
    }
    return reviews.get(code)


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


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, int)]


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _non_goals() -> list[str]:
    return [
        "Does not modify the source registry.",
        "Does not approve source usage or source approval.",
        "Does not fetch remote source pages or download attachments.",
        "Does not create raw snapshots.",
        "Does not parse rows or run quality gates.",
        "Does not write databases, seeds, RAG indexes, or Agent-visible data.",
    ]
