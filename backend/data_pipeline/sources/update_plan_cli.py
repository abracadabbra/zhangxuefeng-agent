"""No-dependency CLI for source registry update planning."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.update_plan import (
    build_source_registry_update_plan,
)


def main(argv: list[str] | None = None) -> int:
    """Plan source registry metadata updates without writing the registry."""
    parser = argparse.ArgumentParser(
        description="Build a no-write source registry update plan",
    )
    parser.add_argument("registry", help="Path to source registry JSON")
    parser.add_argument(
        "approval_review",
        help="Path to source review approval review JSON",
    )
    parser.add_argument(
        "--plan-output",
        help="Optional path to write source registry update plan JSON",
    )
    args = parser.parse_args(argv)

    try:
        plan = build_source_registry_update_plan(
            _read_json(Path(args.registry)),
            _read_json(Path(args.approval_review)),
        )
        if args.plan_output:
            _write_json(Path(args.plan_output), plan)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["passed"] else 1


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
