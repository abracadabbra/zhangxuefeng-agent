"""No-dependency CLI for source registry patch chain smoke checks."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.patch_chain_smoke import (
    build_source_registry_patch_chain_smoke,
)


def main(argv: list[str] | None = None) -> int:
    """Check registry patch approval and preview without mutating data."""
    parser = argparse.ArgumentParser(
        description="Run a no-write source registry patch chain smoke check",
    )
    parser.add_argument("registry", help="Path to source registry JSON")
    parser.add_argument(
        "update_plan",
        help="Path to a source registry update plan JSON file",
    )
    parser.add_argument(
        "patch_approval_review",
        help="Path to a source registry patch approval review JSON file",
    )
    parser.add_argument(
        "--review-output",
        help="Optional path to write registry patch chain smoke JSON",
    )
    args = parser.parse_args(argv)

    try:
        report = build_source_registry_patch_chain_smoke(
            registry_payload=_read_json(Path(args.registry)),
            update_plan=_read_json(Path(args.update_plan)),
            patch_approval_review=_read_json(Path(args.patch_approval_review)),
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
