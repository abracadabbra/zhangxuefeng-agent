"""CLI for real-data evidence artifact inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.data_pipeline.pilots.evidence_inventory import (
    build_evidence_artifact_inventory,
)


def main(argv: list[str] | None = None) -> int:
    """Run a no-write inventory over evidence artifact JSON files."""
    parser = argparse.ArgumentParser(
        description="Inventory real-data evidence artifacts without side effects",
    )
    parser.add_argument(
        "artifacts_dir",
        nargs="?",
        default="examples/real_data/artifacts",
        help="Directory containing evidence artifact JSON files",
    )
    parser.add_argument(
        "--require-artifact",
        action="append",
        dest="required_artifacts",
        help="Artifact filename that must exist; may be repeated",
    )
    parser.add_argument(
        "--inventory-output",
        help="Optional path to write inventory JSON",
    )
    args = parser.parse_args(argv)

    kwargs = {}
    if args.required_artifacts is not None:
        kwargs["required_artifacts"] = args.required_artifacts
    report = build_evidence_artifact_inventory(args.artifacts_dir, **kwargs)
    if args.inventory_output:
        _write_json(Path(args.inventory_output), report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
