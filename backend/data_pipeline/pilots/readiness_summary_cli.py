"""CLI for the real-data MVP readiness summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.data_pipeline.pilots.readiness_summary import (
    build_mvp_readiness_summary_from_paths,
)


def main(argv: list[str] | None = None) -> int:
    """Build a no-write summary of the current MVP readiness state."""
    parser = argparse.ArgumentParser(
        description="Summarize real-data MVP readiness without side effects",
    )
    parser.add_argument(
        "--source-snapshot-planning-review",
        default=(
            "examples/real_data/artifacts/"
            "sd_source_snapshot_planning_blocked.json"
        ),
        help="Source snapshot planning review JSON",
    )
    parser.add_argument(
        "--example-chain-smoke",
        default="examples/real_data/artifacts/sd_example_chain_smoke.json",
        help="Aggregate example chain smoke JSON",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="examples/real_data/artifacts",
        help="Directory containing evidence artifact JSON files",
    )
    parser.add_argument(
        "--source-to-quality-chain-smoke",
        default=(
            "examples/real_data/artifacts/"
            "source_to_quality_chain_smoke_approved_example.json"
        ),
        help="Optional source-to-quality chain smoke JSON",
    )
    parser.add_argument(
        "--usage-to-approval-chain-smoke",
        default=(
            "examples/real_data/artifacts/"
            "source_usage_to_approval_chain_smoke_reviewed_example.json"
        ),
        help="Optional source usage-to-approval chain smoke JSON",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional path to write summary JSON",
    )
    args = parser.parse_args(argv)

    summary = build_mvp_readiness_summary_from_paths(
        source_snapshot_planning_review_path=args.source_snapshot_planning_review,
        example_chain_smoke_path=args.example_chain_smoke,
        artifacts_dir=args.artifacts_dir,
        source_to_quality_chain_smoke_path=args.source_to_quality_chain_smoke,
        usage_to_approval_chain_smoke_path=args.usage_to_approval_chain_smoke,
    )
    if args.summary_output:
        _write_json(Path(args.summary_output), summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] else 1


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
