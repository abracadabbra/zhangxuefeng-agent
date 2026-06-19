"""No-dependency CLI for official dataset year review packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.year_review import review_source_years


def main(argv: list[str] | None = None) -> int:
    """Review official dataset years without mutating source registry data."""
    parser = argparse.ArgumentParser(
        description="Review a no-write source year packet",
    )
    parser.add_argument("year_review", help="Path to source year review JSON")
    parser.add_argument(
        "--review-output",
        help="Optional path to write source year review JSON",
    )
    args = parser.parse_args(argv)

    try:
        review = review_source_years(_read_json(Path(args.year_review)))
        if args.review_output:
            _write_json(Path(args.review_output), review)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review["passed"] else 1


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
