"""CLI for source-to-intake through quality readiness chain smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.pilots.source_to_quality_chain_smoke import (
    build_source_to_quality_chain_smoke,
)


def main(argv: list[str] | None = None) -> int:
    """Run the source-to-quality no-write chain smoke."""
    parser = argparse.ArgumentParser(
        description="Run source approval through quality readiness chain smoke",
    )
    parser.add_argument("--source-to-intake-chain", required=True)
    parser.add_argument("--parser-smoke-review", required=True)
    parser.add_argument("--quality-smoke-review", required=True)
    parser.add_argument("--review-output", help="Optional path to write review")
    args = parser.parse_args(argv)

    try:
        report = build_source_to_quality_chain_smoke(
            source_to_intake_chain=_read_json(Path(args.source_to_intake_chain)),
            parser_smoke_review=_read_json(Path(args.parser_smoke_review)),
            quality_smoke_review=_read_json(Path(args.quality_smoke_review)),
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
