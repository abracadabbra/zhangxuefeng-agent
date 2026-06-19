"""No-dependency CLI for pilot artifact manifest smoke review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.pilots.artifact_smoke import (
    build_pilot_artifact_smoke_review,
)


def main(argv: list[str] | None = None) -> int:
    """Review a pilot artifact manifest without importing pydantic contracts."""
    parser = argparse.ArgumentParser(
        description="Run a no-dependency pilot artifact manifest smoke review",
    )
    parser.add_argument("manifest", help="Path to a pilot artifact manifest JSON")
    parser.add_argument("--review-output", help="Optional path to write review JSON")
    parser.add_argument("--expect-source-id", help="Expected source_id")
    parser.add_argument("--expect-snapshot-id", help="Expected snapshot_id")
    parser.add_argument("--expect-dataset", help="Expected dataset")
    parser.add_argument(
        "--skip-path-checks",
        action="store_true",
        help="Skip local artifact path existence checks",
    )
    args = parser.parse_args(argv)

    try:
        report = build_pilot_artifact_smoke_review(
            _read_json(Path(args.manifest)),
            expected_source_id=args.expect_source_id,
            expected_snapshot_id=args.expect_snapshot_id,
            expected_dataset=args.expect_dataset,
            check_paths=not args.skip_path_checks,
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
