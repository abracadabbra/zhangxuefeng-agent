"""No-write CLI for official sample intake review."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.intake.review import review_intake_payload


def main(argv: list[str] | None = None) -> int:
    """Review an official sample intake packet and print a JSON report."""
    parser = argparse.ArgumentParser(
        description="Review an official sample intake packet",
    )
    parser.add_argument("intake_path", help="Path to an intake JSON file")
    parser.add_argument(
        "--review-output",
        help="Optional path to write the intake review JSON",
    )
    args = parser.parse_args(argv)

    try:
        payload = _read_json(Path(args.intake_path))
        report = review_intake_payload(payload)
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
        raise TypeError("intake payload must be a JSON object")
    return payload


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
