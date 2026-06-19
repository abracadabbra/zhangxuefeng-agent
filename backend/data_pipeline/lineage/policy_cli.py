"""No-write CLI for Agent answer source policy review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.lineage.policy import build_answer_source_policy


def main(argv: list[str] | None = None) -> int:
    """Review source-summary JSON and print an answer source policy report."""
    parser = argparse.ArgumentParser(
        description="Review Agent answer source policy from source_summary JSON",
    )
    parser.add_argument(
        "summary_path",
        help="Path to a tool response JSON or source_summary JSON file",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Treat the whole JSON file as the source_summary object.",
    )
    parser.add_argument(
        "--policy-output",
        help="Optional path to write the answer source policy review JSON",
    )
    args = parser.parse_args(argv)

    try:
        payload = _read_json(Path(args.summary_path))
        source_summary = _extract_source_summary(
            payload,
            summary_only=args.summary_only,
        )
        report = _build_report(source_summary)
        if args.policy_output:
            _write_json(Path(args.policy_output), report)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise TypeError("answer policy input must be a JSON object")
    return payload


def _extract_source_summary(
    payload: dict[str, Any],
    *,
    summary_only: bool,
) -> dict[str, Any]:
    source_summary = payload if summary_only else payload.get("source_summary")
    if not isinstance(source_summary, dict):
        raise ValueError("source_summary must be a JSON object")
    return source_summary


def _build_report(source_summary: dict[str, Any]) -> dict[str, Any]:
    answer_source_policy = build_answer_source_policy(source_summary)
    return {
        "action": "answer_source_policy_review",
        "passed": answer_source_policy["answer_mode"] != "unsupported",
        "source_summary": source_summary,
        "answer_source_policy": answer_source_policy,
        "non_goals": [
            "does_not_fetch_remote_data",
            "does_not_write_database",
            "does_not_refresh_rag_or_agent",
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
