"""CLI for priority source year review coverage reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.year_review_coverage import (
    build_source_year_review_coverage_report,
)


def main(argv: list[str] | None = None) -> int:
    """Build a no-write coverage report for source year review artifacts."""
    parser = argparse.ArgumentParser(
        description="Build a priority source year review coverage report",
    )
    parser.add_argument("coverage_report", help="Path to source coverage JSON")
    parser.add_argument(
        "--artifacts-dir",
        help="Directory containing source year review artifacts",
    )
    parser.add_argument(
        "--year-review-artifact",
        action="append",
        default=[],
        help="Additional source year review artifact path",
    )
    parser.add_argument("--report-output", help="Optional path to write report")
    args = parser.parse_args(argv)

    try:
        report = build_source_year_review_coverage_report(
            _read_json(Path(args.coverage_report)),
            _load_year_reviews(args.artifacts_dir, args.year_review_artifact),
        )
        if args.report_output:
            _write_json(Path(args.report_output), report)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def _load_year_reviews(
    artifacts_dir: str | None,
    artifact_paths: list[str],
) -> list[dict[str, Any]]:
    paths = [Path(path) for path in artifact_paths]
    if artifacts_dir:
        paths.extend(sorted(Path(artifacts_dir).glob("*.json")))
    reviews = []
    for path in paths:
        payload = _read_json(path)
        if payload.get("action") == "source_year_review":
            reviews.append(payload)
    return reviews


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _error_payload(exc: Exception) -> dict[str, str]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
