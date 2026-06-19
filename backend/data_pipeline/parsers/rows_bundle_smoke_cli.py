"""CLI for stdlib-only parser rows bundle smoke review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.parsers.rows_bundle_smoke import (
    build_parser_rows_bundle_smoke,
)


def main(argv: list[str] | None = None) -> int:
    """Run a no-write parser rows bundle smoke review."""
    parser = argparse.ArgumentParser(
        description="Review normalized parser rows without pydantic imports",
    )
    parser.add_argument("rows_bundle", help="Path to rows bundle JSON")
    parser.add_argument(
        "--snapshot-manifest",
        help="Optional raw snapshot manifest JSON for scope binding",
    )
    parser.add_argument("--expect-source-id", help="Expected source_id")
    parser.add_argument("--expect-snapshot-id", help="Expected snapshot_id")
    parser.add_argument("--expect-dataset", help="Expected dataset")
    parser.add_argument("--review-output", help="Optional path to write review")
    args = parser.parse_args(argv)

    try:
        report = build_parser_rows_bundle_smoke(
            _read_json(Path(args.rows_bundle)),
            snapshot_manifest=(
                _read_json(Path(args.snapshot_manifest))
                if args.snapshot_manifest
                else None
            ),
            expected_source_id=args.expect_source_id,
            expected_snapshot_id=args.expect_snapshot_id,
            expected_dataset=args.expect_dataset,
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
