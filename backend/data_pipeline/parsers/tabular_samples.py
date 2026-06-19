"""Parser for reviewed tabular pilot rows.

This module handles CSV-like rows after a human has already downloaded,
preserved, and reviewed an official file. It does not fetch remote files or
parse provider-specific spreadsheets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.data_pipeline.quality.candidates import CanonicalCandidate
    from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest


INT_FIELDS = {
    "year",
    "min_score",
    "avg_score",
    "max_score",
    "min_rank",
    "plan_count",
    "duration",
    "tuition",
}
FLOAT_FIELDS = {"confidence"}
REVIEW_PREFIX = "review."


class ReviewedTabularSampleParser:
    """Normalize reviewed CSV-like rows before manual sample parsing."""

    def __init__(self, *, dataset: str | None = None):
        self.dataset = dataset

    def parse(
        self,
        rows: list[dict[str, Any]],
        manifest: RawSnapshotManifest,
    ) -> list[CanonicalCandidate]:
        from backend.data_pipeline.parsers.manual_samples import ManualSampleParser

        normalized_rows = normalize_tabular_rows(rows, dataset=self.dataset)
        return ManualSampleParser().parse(normalized_rows, manifest)


def normalize_tabular_rows(
    rows: list[dict[str, Any]],
    *,
    dataset: str | None = None,
) -> list[dict[str, Any]]:
    """Return JSON-ready normalized rows from reviewed tabular records."""
    return [
        normalize_tabular_row(row, dataset=dataset)
        for row in rows
    ]


def normalize_tabular_row(
    row: dict[str, Any],
    *,
    dataset: str | None = None,
) -> dict[str, Any]:
    """Normalize one reviewed tabular row into the manual sample row shape."""
    normalized: dict[str, Any] = {}
    review: dict[str, Any] = {}

    for raw_key, raw_value in row.items():
        key = str(raw_key).strip()
        if not key:
            continue

        value = _normalize_cell(raw_value)
        if key.startswith(REVIEW_PREFIX):
            review_key = key[len(REVIEW_PREFIX):]
            if value is not None:
                review[review_key] = value
            continue

        normalized[key] = _coerce_field(key, value)

    if dataset and not normalized.get("dataset"):
        normalized["dataset"] = dataset
    if review:
        normalized["review"] = review

    return normalized


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def _coerce_field(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in INT_FIELDS:
        return _coerce_int(key, value)
    if key in FLOAT_FIELDS:
        return _coerce_float(key, value)
    return value


def _coerce_int(key: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer, got boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be an integer: {value}") from exc
        if parsed.is_integer():
            return int(parsed)
    raise ValueError(f"{key} must be an integer: {value}")


def _coerce_float(key: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a number, got boolean")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be a number: {value}") from exc
    raise ValueError(f"{key} must be a number: {value}")
