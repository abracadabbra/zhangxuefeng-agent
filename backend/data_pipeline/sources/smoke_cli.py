"""No-dependency CLI for source registry structural smoke review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.smoke import build_source_registry_smoke_review


def main(argv: list[str] | None = None) -> int:
    """Review source registry JSON without importing pydantic contracts."""
    parser = argparse.ArgumentParser(
        description="Run a no-dependency source registry smoke review",
    )
    parser.add_argument(
        "registry",
        help="Path to a source registry JSON file",
    )
    parser.add_argument(
        "--review-output",
        help="Optional path to write source registry smoke review JSON",
    )
    parser.add_argument(
        "--expect-source-id",
        action="append",
        default=[],
        help="Expected source_id. Repeat for multiple sources.",
    )
    parser.add_argument(
        "--expect-province",
        action="append",
        default=[],
        help="Expected covered province. Repeat for multiple provinces.",
    )
    parser.add_argument(
        "--expect-data-category",
        action="append",
        default=[],
        help="Expected data category. Repeat for multiple categories.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_source_registry_smoke_review(
            _read_json(Path(args.registry)),
            expected_source_ids=args.expect_source_id,
            expected_provinces=args.expect_province,
            expected_data_categories=args.expect_data_category,
        )
        if args.review_output:
            _write_json(Path(args.review_output), report)
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
