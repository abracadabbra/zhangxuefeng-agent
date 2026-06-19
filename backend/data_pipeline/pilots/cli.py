"""Command-line entry point for manual pilot dry-runs."""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.data_pipeline.loaders import build_loader_approval_packet
from backend.data_pipeline.pilots.dry_run import (
    build_load_ready_candidates_bundle,
    build_load_ready_candidates_snapshot_dir,
    PilotSnapshotDirBundle,
    run_manual_pilot_bundle,
    run_manual_pilot_snapshot_dir_bundle,
)
from backend.data_pipeline.quality.candidates import CanonicalCandidate
from backend.data_pipeline.quality.checks import QualityGateConfig
from backend.data_pipeline.sources.registry import DataSource


def main(argv: list[str] | None = None) -> int:
    """Run a pilot dry-run bundle and print the audit report as JSON."""
    parser = argparse.ArgumentParser(description="Run a manual data pilot dry-run")
    parser.add_argument("bundle", help="Path to a JSON bundle with source, manifest, and rows")
    parser.add_argument(
        "--snapshot-dir",
        help="Optional local raw snapshot directory with manifest.json and files",
    )
    parser.add_argument(
        "--audit-output",
        help="Optional path to write the audit report JSON for review",
    )
    parser.add_argument(
        "--approval-output",
        help="Optional path to write a loader approval packet JSON",
    )
    parser.add_argument(
        "--parser-name",
        default="ManualSampleParser",
        help="Parser name to include in approval packets",
    )
    parser.add_argument(
        "--parser-version",
        default="0.1.0",
        help="Parser version to include in approval packets",
    )
    args = parser.parse_args(argv)

    try:
        payload = _read_json(Path(args.bundle))
        if args.snapshot_dir:
            audit = run_manual_pilot_snapshot_dir_bundle(
                payload,
                Path(args.snapshot_dir),
            )
        else:
            audit = run_manual_pilot_bundle(payload)
        if args.audit_output:
            _write_json(Path(args.audit_output), audit)
        if args.approval_output:
            candidates = _build_candidates_for_approval(
                payload,
                snapshot_dir=args.snapshot_dir,
            )
            approval = build_loader_approval_packet(
                audit=audit,
                candidates=candidates,
                parser_name=args.parser_name,
                parser_version=args.parser_version,
            ).to_review_dict()
            _write_json(Path(args.approval_output), approval)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, ValidationError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["passed"] else 1


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_candidates_for_approval(
    payload: dict[str, Any],
    *,
    snapshot_dir: str | None,
) -> list[CanonicalCandidate]:
    if snapshot_dir:
        bundle = PilotSnapshotDirBundle.model_validate(payload)
        source = (
            DataSource.model_validate(bundle.source)
            if bundle.source is not None
            else None
        )
        config = (
            QualityGateConfig.model_validate(bundle.quality_config)
            if bundle.quality_config is not None
            else None
        )
        return build_load_ready_candidates_snapshot_dir(
            bundle.rows,
            Path(snapshot_dir),
            config,
            source=source,
            manifest_name=bundle.manifest_name,
        )

    return build_load_ready_candidates_bundle(payload)


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
