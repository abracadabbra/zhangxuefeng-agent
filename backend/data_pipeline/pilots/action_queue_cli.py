"""CLI for the real-data MVP no-write action queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.pilots.action_queue import build_mvp_action_queue


def main(argv: list[str] | None = None) -> int:
    """Build a human action queue from no-write review artifacts."""
    parser = argparse.ArgumentParser(
        description="Build real-data MVP action queue without side effects",
    )
    parser.add_argument(
        "--readiness-summary",
        default="examples/real_data/artifacts/sd_mvp_readiness_summary.json",
    )
    parser.add_argument(
        "--source-review-handoff",
        default="examples/real_data/artifacts/sd_source_review_handoff_blocked.json",
    )
    parser.add_argument("--review-output", help="Optional path to write queue JSON")
    args = parser.parse_args(argv)

    try:
        report = build_mvp_action_queue(
            readiness_summary=_read_json(Path(args.readiness_summary)),
            source_review_handoff=_read_json(Path(args.source_review_handoff)),
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
