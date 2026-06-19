"""No-write CLI for canonical loader run evidence review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.activation.loader_evidence import (
    build_loader_run_evidence_review,
)


def main(argv: list[str] | None = None) -> int:
    """Review a loader run record against a pilot artifact manifest."""
    parser = argparse.ArgumentParser(
        description="Review canonical loader run evidence before Agent visibility",
    )
    parser.add_argument(
        "--artifact-manifest",
        required=True,
        help="Path to pilot artifact manifest JSON",
    )
    parser.add_argument(
        "--loader-run-record",
        required=True,
        help="Path to canonical loader run record JSON",
    )
    parser.add_argument(
        "--review-output",
        help="Optional path to write loader run evidence review JSON",
    )
    args = parser.parse_args(argv)

    try:
        artifact_manifest_path = Path(args.artifact_manifest)
        report = build_loader_run_evidence_review(
            artifact_manifest=_read_json(artifact_manifest_path),
            artifact_manifest_path=str(artifact_manifest_path),
            loader_run_record=_read_json(Path(args.loader_run_record)),
        )
        if args.review_output:
            _write_json(Path(args.review_output), report)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_activation_evidence"] else 1


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
