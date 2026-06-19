"""No-dependency CLI for source registry patch approval packets."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.patch_approval import (
    review_source_registry_patch_approval,
)


def main(argv: list[str] | None = None) -> int:
    """Review a source registry patch approval without mutating registry data."""
    parser = argparse.ArgumentParser(
        description="Review a no-write source registry patch approval packet",
    )
    parser.add_argument(
        "update_plan",
        help="Path to a source registry update plan JSON file",
    )
    parser.add_argument(
        "approval",
        help="Path to a source registry patch approval JSON file",
    )
    parser.add_argument(
        "--review-output",
        help="Optional path to write registry patch approval review JSON",
    )
    args = parser.parse_args(argv)

    try:
        review = review_source_registry_patch_approval(
            _read_json(Path(args.update_plan)),
            _read_json(Path(args.approval)),
        )
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
