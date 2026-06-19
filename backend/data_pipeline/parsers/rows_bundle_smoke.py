"""Stdlib-only smoke review for parser rows bundles."""

from __future__ import annotations

from typing import Any


NATURAL_KEY_FIELDS = {
    "admission_scores": (
        "school_name",
        "province",
        "year",
        "batch",
        "subject_type",
    ),
    "enrollment_plans": (
        "school_name",
        "major_name",
        "province",
        "year",
    ),
}
VALUE_FIELDS = {
    "admission_scores": (
        "min_score",
        "avg_score",
        "max_score",
        "min_rank",
        "plan_count",
    ),
    "enrollment_plans": (
        "plan_count",
        "subject_requirement",
        "batch",
        "duration",
        "tuition",
    ),
}
ENTITY_TYPES = {
    "admission_scores": "admission_score",
    "enrollment_plans": "enrollment_plan",
}
REQUIRED_REVIEW_FIELDS = ("reviewed_by", "reviewed_at")


def build_parser_rows_bundle_smoke(
    rows_bundle: dict[str, Any],
    *,
    snapshot_manifest: dict[str, Any] | None = None,
    expected_source_id: str | None = None,
    expected_snapshot_id: str | None = None,
    expected_dataset: str | None = None,
) -> dict[str, Any]:
    """Build a no-write parser-readiness smoke report for normalized rows."""
    issues: list[dict[str, Any]] = []
    rows = _rows(rows_bundle, issues)
    source = _object(rows_bundle.get("source"))
    quality_config = _object(rows_bundle.get("quality_config"))
    dataset = _infer_dataset(rows_bundle, snapshot_manifest, expected_dataset)
    source_id = _source_id(source, snapshot_manifest)
    snapshot_id = _manifest_str(snapshot_manifest, "snapshot_id")

    _check_scope(
        issues,
        source_id=source_id,
        snapshot_id=snapshot_id,
        dataset=dataset,
        expected_source_id=expected_source_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_dataset=expected_dataset,
    )

    candidate_previews = [
        _candidate_preview(
            index,
            row,
            dataset,
            source_id=source_id,
            snapshot_id=snapshot_id,
            require_review_metadata=bool(
                quality_config.get("require_review_metadata")
            ),
            issues=issues,
        )
        for index, row in enumerate(rows, start=1)
    ]

    issue_counts = _issue_counts(issues)
    return {
        "action": "parser_rows_bundle_smoke",
        "passed": issue_counts["error"] == 0,
        "ready_for_parser": issue_counts["error"] == 0,
        "scope": {
            "source_id": source_id,
            "snapshot_id": snapshot_id,
            "dataset": dataset,
            "row_count": len(rows),
        },
        "candidate_previews": candidate_previews,
        "issue_counts": issue_counts,
        "issues": issues,
        "required_reviews": _required_reviews(issues),
        "non_goals": [
            "Does not fetch remote data.",
            "Does not create raw snapshots.",
            "Does not execute the pydantic parser contract.",
            "Does not run the quality gate.",
            "Does not write database rows or seed data.",
            "Does not approve loader execution.",
            "Does not refresh RAG or Agent-visible data.",
        ],
    }


def _rows(rows_bundle: dict[str, Any], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = rows_bundle.get("rows")
    if not isinstance(rows, list):
        issues.append(_issue(
            "error",
            "invalid_rows",
            "rows_bundle.rows must be a list",
            "rows",
        ))
        return []
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            normalized_rows.append(row)
        else:
            issues.append(_issue(
                "error",
                "invalid_row",
                "each rows_bundle row must be an object",
                f"rows[{index}]",
            ))
    if not rows:
        issues.append(_issue("error", "empty_rows", "rows must not be empty", "rows"))
    return normalized_rows


def _candidate_preview(
    index: int,
    row: dict[str, Any],
    dataset: str | None,
    *,
    source_id: str | None,
    snapshot_id: str | None,
    require_review_metadata: bool,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    row_dataset = row.get("dataset") or dataset
    if row_dataset not in ENTITY_TYPES:
        issues.append(_issue(
            "error",
            "unsupported_dataset",
            f"unsupported parser dataset: {row_dataset}",
            f"rows[{index}].dataset",
        ))
        natural_key: dict[str, Any] = {}
        values: dict[str, Any] = {}
        entity_type = None
    else:
        natural_key = {
            field: row.get(field)
            for field in NATURAL_KEY_FIELDS[row_dataset]
        }
        values = {
            field: row.get(field)
            for field in VALUE_FIELDS[row_dataset]
        }
        entity_type = ENTITY_TYPES[row_dataset]
        _check_required_values(index, natural_key, issues)

    review = _object(row.get("review"))
    if require_review_metadata:
        _check_review_metadata(index, review, issues)

    return {
        "row_index": index,
        "entity_type": entity_type,
        "natural_key": natural_key,
        "values": values,
        "source": {
            "source_id": source_id,
            "snapshot_id": snapshot_id,
            "dataset": row_dataset,
            "year": natural_key.get("year"),
            "source_record_ref": row.get("source_record_ref") or f"manual_row={index}",
            "confidence": row.get("confidence", 0.95),
            "has_review_metadata": bool(review),
        },
    }


def _check_required_values(
    index: int,
    natural_key: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    for field, value in natural_key.items():
        if value is None or value == "":
            issues.append(_issue(
                "error",
                "missing_natural_key_field",
                f"natural key field is required: {field}",
                f"rows[{index}].{field}",
            ))


def _check_review_metadata(
    index: int,
    review: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    for field in REQUIRED_REVIEW_FIELDS:
        if not review.get(field):
            issues.append(_issue(
                "error",
                "missing_review_metadata",
                f"review metadata field is required: {field}",
                f"rows[{index}].review.{field}",
            ))


def _infer_dataset(
    rows_bundle: dict[str, Any],
    snapshot_manifest: dict[str, Any] | None,
    expected_dataset: str | None,
) -> str | None:
    if expected_dataset:
        return expected_dataset
    manifest_dataset = _manifest_str(snapshot_manifest, "dataset")
    if manifest_dataset:
        return manifest_dataset
    categories = _object(rows_bundle.get("source")).get("data_categories")
    if isinstance(categories, list) and len(categories) == 1:
        return categories[0]
    return None


def _check_scope(
    issues: list[dict[str, Any]],
    *,
    source_id: str | None,
    snapshot_id: str | None,
    dataset: str | None,
    expected_source_id: str | None,
    expected_snapshot_id: str | None,
    expected_dataset: str | None,
) -> None:
    expectations = {
        "source_id": (source_id, expected_source_id),
        "snapshot_id": (snapshot_id, expected_snapshot_id),
        "dataset": (dataset, expected_dataset),
    }
    for field, (actual, expected) in expectations.items():
        if expected is not None and actual != expected:
            issues.append(_issue(
                "error",
                f"unexpected_{field}",
                f"{field} does not match expected value",
                f"scope.{field}",
            ))
    for field, actual in {
        "source_id": source_id,
        "dataset": dataset,
    }.items():
        if not actual:
            issues.append(_issue(
                "error",
                f"missing_{field}",
                f"{field} is required for parser smoke",
                f"scope.{field}",
            ))


def _source_id(
    source: dict[str, Any],
    snapshot_manifest: dict[str, Any] | None,
) -> str | None:
    return source.get("source_id") or _manifest_str(snapshot_manifest, "source_id")


def _manifest_str(
    snapshot_manifest: dict[str, Any] | None,
    field: str,
) -> str | None:
    if not isinstance(snapshot_manifest, dict):
        return None
    value = snapshot_manifest.get(field)
    return value if isinstance(value, str) and value else None


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _issue_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _required_reviews(issues: list[dict[str, Any]]) -> list[str]:
    messages = []
    if any(issue["code"] == "missing_review_metadata" for issue in issues):
        messages.append("Fill row review metadata before parser handoff.")
    if any(issue["code"] == "missing_natural_key_field" for issue in issues):
        messages.append("Fill parser natural-key fields before quality gate.")
    if any(issue["code"] == "unsupported_dataset" for issue in issues):
        messages.append("Use a supported parser dataset.")
    return messages


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
