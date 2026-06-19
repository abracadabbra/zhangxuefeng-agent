"""Command-line entry point for pilot artifact manifests."""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.data_pipeline.pilots.artifacts import build_pilot_artifact_manifest


def main(argv: list[str] | None = None) -> int:
    """Build a review manifest from existing pilot artifact JSON files."""
    parser = argparse.ArgumentParser(description="Build a pilot artifact manifest")
    parser.add_argument("--source-audit", required=True, help="Path to source audit JSON")
    parser.add_argument("--intake-review", help="Optional intake review JSON")
    parser.add_argument("--dry-run-audit", required=True, help="Path to dry-run audit JSON")
    parser.add_argument("--rows-bundle", required=True, help="Path to rows bundle JSON")
    parser.add_argument("--snapshot-dir", help="Optional local raw snapshot directory")
    parser.add_argument("--loader-approval", help="Optional loader approval JSON")
    parser.add_argument("--manifest-output", help="Optional path to write manifest JSON")
    args = parser.parse_args(argv)

    try:
        source_audit_path = Path(args.source_audit)
        intake_review_path = (
            Path(args.intake_review)
            if args.intake_review is not None
            else None
        )
        dry_run_audit_path = Path(args.dry_run_audit)
        loader_approval_path = (
            Path(args.loader_approval)
            if args.loader_approval is not None
            else None
        )
        manifest = build_pilot_artifact_manifest(
            source_audit=_read_json(source_audit_path),
            intake_review=(
                _read_json(intake_review_path)
                if intake_review_path is not None
                else None
            ),
            dry_run_audit=_read_json(dry_run_audit_path),
            loader_approval=(
                _read_json(loader_approval_path)
                if loader_approval_path is not None
                else None
            ),
            source_audit_path=str(source_audit_path),
            intake_review_path=(
                str(intake_review_path)
                if intake_review_path is not None
                else None
            ),
            dry_run_audit_path=str(dry_run_audit_path),
            loader_approval_path=(
                str(loader_approval_path)
                if loader_approval_path is not None
                else None
            ),
            rows_bundle_path=args.rows_bundle,
            snapshot_dir=args.snapshot_dir,
            artifact_path_issues=_artifact_path_issues(
                rows_bundle_path=Path(args.rows_bundle),
                snapshot_dir=(
                    Path(args.snapshot_dir)
                    if args.snapshot_dir is not None
                    else None
                ),
            ),
        ).to_review_dict()
        if args.manifest_output:
            _write_json(Path(args.manifest_output), manifest)
    except (json.JSONDecodeError, OSError, TypeError, ValueError, ValidationError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["ready_for_loader_execution"] else 1


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


def _artifact_path_issues(
    *,
    rows_bundle_path: Path,
    snapshot_dir: Path | None,
) -> list[str]:
    issues = []
    if not rows_bundle_path.is_file():
        issues.append(f"missing file: rows_bundle:{rows_bundle_path}")
    if snapshot_dir is not None and not snapshot_dir.is_dir():
        issues.append(f"missing directory: snapshot_dir:{snapshot_dir}")
    return issues


def _error_payload(exc: Exception) -> dict[str, str]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
