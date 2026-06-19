"""No-dependency CLI for source registry patch previews."""

import argparse
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.sources.patch_preview import (
    build_source_registry_patch_preview,
)


def main(argv: list[str] | None = None) -> int:
    """Build a source registry patch preview without mutating registry data."""
    parser = argparse.ArgumentParser(
        description="Build a no-write source registry patch preview",
    )
    parser.add_argument("registry", help="Path to source registry JSON")
    parser.add_argument(
        "update_plan",
        help="Path to a source registry update plan JSON file",
    )
    parser.add_argument(
        "patch_approval_review",
        help="Path to a source registry patch approval review JSON file",
    )
    parser.add_argument(
        "--preview-output",
        help="Optional path to write source registry patch preview JSON",
    )
    args = parser.parse_args(argv)

    try:
        preview = build_source_registry_patch_preview(
            _read_json(Path(args.registry)),
            _read_json(Path(args.update_plan)),
            _read_json(Path(args.patch_approval_review)),
        )
        if args.preview_output:
            _write_json(Path(args.preview_output), preview)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(preview, ensure_ascii=False, indent=2))
    return 0 if preview["passed"] else 1


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
