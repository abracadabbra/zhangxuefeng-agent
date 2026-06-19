"""Stdlib-only smoke from source approval evidence through quality readiness."""

from __future__ import annotations

from typing import Any


def build_source_to_quality_chain_smoke(
    *,
    source_to_intake_chain: dict[str, Any],
    parser_smoke_review: dict[str, Any],
    quality_smoke_review: dict[str, Any],
) -> dict[str, Any]:
    """Check source-to-intake, parser, and quality evidence continuity."""
    checks = {
        "source_to_intake_chain_passed": (
            source_to_intake_chain.get("passed") is True
        ),
        "parser_smoke_ready": parser_smoke_review.get("ready_for_parser") is True,
        "quality_smoke_ready": (
            quality_smoke_review.get("ready_for_quality_gate") is True
        ),
        "source_scope_matches_parser": _source_scope_matches_parser(
            source_to_intake_chain,
            parser_smoke_review,
        ),
        "parser_scope_matches_quality": _parser_scope_matches_quality(
            parser_smoke_review,
            quality_smoke_review,
        ),
        "quality_source_metadata_matches_parser": (
            _quality_source_metadata_matches_parser(
                parser_smoke_review,
                quality_smoke_review,
            )
        ),
        "candidate_year_matches_source_scope": (
            _candidate_year_matches_source_scope(
                source_to_intake_chain,
                parser_smoke_review,
                quality_smoke_review,
            )
        ),
    }
    issues = _issues_from_checks(checks)
    issue_counts = {"error": len(issues), "warning": 0, "info": 0}
    return {
        "action": "source_to_quality_chain_smoke",
        "passed": issue_counts["error"] == 0,
        "scope": _scope(
            source_to_intake_chain,
            parser_smoke_review,
            quality_smoke_review,
        ),
        "checks": checks,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(
            source_to_intake_chain,
            parser_smoke_review,
            quality_smoke_review,
        ),
        "reviews": {
            "source_to_intake_chain": source_to_intake_chain,
            "parser_rows_bundle_smoke": parser_smoke_review,
            "quality_smoke": quality_smoke_review,
        },
        "non_goals": [
            "Does not modify sources.json.",
            "Does not approve any real source.",
            "Does not fetch remote data or download official attachments.",
            "Does not create raw snapshots.",
            "Does not execute the pydantic parser contract.",
            "Does not execute the pydantic quality gate.",
            "Does not execute canonical loader.",
            "Does not write database rows, seed data, RAG indexes, or Agent data.",
        ],
    }


def _source_scope_matches_parser(
    source_to_intake_chain: dict[str, Any],
    parser_smoke_review: dict[str, Any],
) -> bool:
    source_scope = _object(source_to_intake_chain.get("scope"))
    parser_scope = _object(parser_smoke_review.get("scope"))
    return (
        source_scope.get("source_id") == parser_scope.get("source_id")
        and source_scope.get("dataset") == parser_scope.get("dataset")
    )


def _parser_scope_matches_quality(
    parser_smoke_review: dict[str, Any],
    quality_smoke_review: dict[str, Any],
) -> bool:
    parser_scope = _object(parser_smoke_review.get("scope"))
    quality_scope = _object(quality_smoke_review.get("scope"))
    return (
        parser_scope.get("source_id") == quality_scope.get("source_id")
        and parser_scope.get("snapshot_id") == quality_scope.get("snapshot_id")
        and parser_scope.get("dataset") == quality_scope.get("dataset")
        and parser_scope.get("row_count") == quality_scope.get("candidate_count")
    )


def _quality_source_metadata_matches_parser(
    parser_smoke_review: dict[str, Any],
    quality_smoke_review: dict[str, Any],
) -> bool:
    parser_scope = _object(parser_smoke_review.get("scope"))
    source_metadata = _object(quality_smoke_review.get("source_metadata"))
    return (
        _single_value(source_metadata.get("source_ids")) == parser_scope.get("source_id")
        and _single_value(source_metadata.get("snapshot_ids"))
        == parser_scope.get("snapshot_id")
        and _single_value(source_metadata.get("datasets")) == parser_scope.get("dataset")
        and source_metadata.get("missing_source_ids") == 0
        and source_metadata.get("missing_snapshot_ids") == 0
    )


def _candidate_year_matches_source_scope(
    source_to_intake_chain: dict[str, Any],
    parser_smoke_review: dict[str, Any],
    quality_smoke_review: dict[str, Any],
) -> bool:
    expected_year = _object(source_to_intake_chain.get("scope")).get("year")
    parser_years = _candidate_source_years(parser_smoke_review)
    quality_year = _single_value(
        _object(quality_smoke_review.get("source_metadata")).get("years"),
    )
    return (
        expected_year is not None
        and parser_years == [expected_year]
        and quality_year == expected_year
    )


def _candidate_source_years(parser_smoke_review: dict[str, Any]) -> list[Any]:
    years = []
    for candidate in parser_smoke_review.get("candidate_previews") or []:
        if not isinstance(candidate, dict):
            continue
        source = _object(candidate.get("source"))
        year = source.get("year")
        if year not in years:
            years.append(year)
    return years


def _scope(
    source_to_intake_chain: dict[str, Any],
    parser_smoke_review: dict[str, Any],
    quality_smoke_review: dict[str, Any],
) -> dict[str, Any]:
    source_scope = _object(source_to_intake_chain.get("scope"))
    parser_scope = _object(parser_smoke_review.get("scope"))
    quality_scope = _object(quality_smoke_review.get("scope"))
    return {
        "source_id": (
            source_scope.get("source_id")
            or parser_scope.get("source_id")
            or quality_scope.get("source_id")
        ),
        "snapshot_id": (
            parser_scope.get("snapshot_id")
            or quality_scope.get("snapshot_id")
        ),
        "dataset": (
            source_scope.get("dataset")
            or parser_scope.get("dataset")
            or quality_scope.get("dataset")
        ),
        "province": source_scope.get("province"),
        "year": source_scope.get("year"),
        "candidate_count": quality_scope.get("candidate_count"),
    }


def _issues_from_checks(checks: dict[str, bool]) -> list[dict[str, str]]:
    issues = []
    for check, passed in checks.items():
        if not passed:
            issues.append({
                "severity": "error",
                "code": f"{check}_failed",
                "message": f"source-to-quality chain check failed: {check}",
                "field": f"checks.{check}",
            })
    return issues


def _required_reviews(*reviews: dict[str, Any]) -> list[str]:
    aggregated = []
    seen = set()
    for review in reviews:
        for item in review.get("required_reviews") or []:
            if isinstance(item, str) and item not in seen:
                aggregated.append(item)
                seen.add(item)
    return aggregated


def _single_value(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return None


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
