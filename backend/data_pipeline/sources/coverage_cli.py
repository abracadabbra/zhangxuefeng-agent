"""No-dependency CLI for source registry coverage reports."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.coverage import build_source_coverage_report


def main(argv: list[str] | None = None) -> int:
    """Build a source coverage report without importing pydantic contracts."""
    parser = argparse.ArgumentParser(
        description="Build a no-dependency source registry coverage report",
    )
    parser.add_argument(
        "registry",
        help="Path to a source registry JSON file",
    )
    parser.add_argument(
        "--report-output",
        help="Optional path to write source coverage report JSON",
    )
    parser.add_argument(
        "--priority-province",
        action="append",
        default=[],
        help="Priority province to track. Repeat for multiple provinces.",
    )
    parser.add_argument(
        "--priority-data-category",
        action="append",
        default=[],
        help="Priority data category to track. Repeat for multiple categories.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_source_coverage_report(
            _read_json(Path(args.registry)),
            priority_provinces=args.priority_province,
            priority_data_categories=args.priority_data_category,
        )
        if args.report_output:
            _write_json(Path(args.report_output), report)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


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
