"""CLI for source usage review through source approval readiness smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.usage_to_approval_chain_smoke import (
    build_usage_to_approval_chain_smoke,
)


def main(argv: list[str] | None = None) -> int:
    """Run the source usage-to-approval no-write chain smoke."""
    parser = argparse.ArgumentParser(
        description="Run source usage review through source approval chain smoke",
    )
    parser.add_argument("--usage-review", required=True)
    parser.add_argument("--source-approval-review", required=True)
    parser.add_argument("--review-output", help="Optional path to write review")
    args = parser.parse_args(argv)

    try:
        report = build_usage_to_approval_chain_smoke(
            usage_review=_read_json(Path(args.usage_review)),
            source_approval_review=_read_json(Path(args.source_approval_review)),
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
