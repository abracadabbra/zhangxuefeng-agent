"""No-write CLI for Agent visibility activation review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.activation.review import (
    review_agent_visibility_activation,
)


def main(argv: list[str] | None = None) -> int:
    """Build an Agent visibility activation review from local artifacts."""
    parser = argparse.ArgumentParser(
        description="Review whether real data can become Agent-visible",
    )
    parser.add_argument(
        "--artifact-manifest",
        required=True,
        help="Path to pilot artifact manifest JSON",
    )
    parser.add_argument(
        "--answer-policy-review",
        help="Optional answer source policy review JSON",
    )
    parser.add_argument(
        "--activation-approval",
        help="Optional Agent visibility approval JSON",
    )
    parser.add_argument(
        "--loader-run-evidence-review",
        help="Optional loader run evidence review JSON",
    )
    parser.add_argument(
        "--review-output",
        help="Optional path to write activation review JSON",
    )
    args = parser.parse_args(argv)

    try:
        report = review_agent_visibility_activation(
            artifact_manifest=_read_json(Path(args.artifact_manifest)),
            answer_policy_review=_optional_json(args.answer_policy_review),
            activation_approval=_optional_json(args.activation_approval),
            loader_run_evidence_review=_optional_json(
                args.loader_run_evidence_review,
            ),
        )
        if args.review_output:
            _write_json(Path(args.review_output), report)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_agent_visibility"] else 1


def _optional_json(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return _read_json(Path(path))


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
