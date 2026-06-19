"""CLI for stdlib-only real-data example chain smoke review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.pilots.example_chain_smoke import (
    build_example_chain_smoke_report,
)


def main(argv: list[str] | None = None) -> int:
    """Run the synthetic real-data example chain smoke review."""
    parser = argparse.ArgumentParser(
        description="Run a no-dependency real-data example chain smoke review",
    )
    parser.add_argument("--intake", required=True, help="Path to intake JSON")
    parser.add_argument(
        "--artifact-manifest",
        required=True,
        help="Path to pilot artifact manifest JSON",
    )
    parser.add_argument(
        "--tool-response",
        required=True,
        help="Path to sourced tool response JSON",
    )
    parser.add_argument(
        "--expected-activation-review",
        help="Optional expected blocked activation review JSON",
    )
    parser.add_argument(
        "--activation-approval",
        help="Optional Agent visibility approval JSON",
    )
    parser.add_argument(
        "--loader-run-record",
        help="Optional canonical loader run record JSON",
    )
    parser.add_argument(
        "--parser-smoke-review",
        help="Optional parser rows bundle smoke review JSON",
    )
    parser.add_argument(
        "--quality-smoke-review",
        help="Optional quality smoke review JSON",
    )
    parser.add_argument("--expect-source-id", help="Expected source_id")
    parser.add_argument("--expect-snapshot-id", help="Expected snapshot_id")
    parser.add_argument("--expect-dataset", help="Expected dataset")
    parser.add_argument("--review-output", help="Optional path to write review")
    args = parser.parse_args(argv)

    try:
        artifact_manifest_path = Path(args.artifact_manifest)
        _validate_activation_inputs(args)
        report = build_example_chain_smoke_report(
            intake_payload=_read_json(Path(args.intake)),
            artifact_manifest=_read_json(artifact_manifest_path),
            tool_response=_read_json(Path(args.tool_response)),
            expected_activation_review=(
                _read_json(Path(args.expected_activation_review))
                if args.expected_activation_review
                else None
            ),
            expected_source_id=args.expect_source_id,
            expected_snapshot_id=args.expect_snapshot_id,
            expected_dataset=args.expect_dataset,
            activation_approval=_optional_json(args.activation_approval),
            loader_run_record=_optional_json(args.loader_run_record),
            parser_smoke_review=_optional_json(args.parser_smoke_review),
            quality_smoke_review=_optional_json(args.quality_smoke_review),
            artifact_manifest_path=str(artifact_manifest_path),
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


def _optional_json(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return _read_json(Path(path))


def _validate_activation_inputs(args: argparse.Namespace) -> None:
    has_activation_approval = args.activation_approval is not None
    has_loader_run_record = args.loader_run_record is not None
    if has_activation_approval != has_loader_run_record:
        raise ValueError(
            "--activation-approval and --loader-run-record must be provided together"
        )


def _error_payload(exc: Exception) -> dict[str, str]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
