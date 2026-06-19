"""Command-line entry point for source registry scope audits."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from backend.data_pipeline.sources.registry import SourceRegistry


def main(argv: list[str] | None = None) -> int:
    """Audit registered data sources for a planned pilot scope."""
    parser = argparse.ArgumentParser(description="Audit a data source registry")
    parser.add_argument(
        "registry",
        help="Path to a source registry JSON file",
    )
    parser.add_argument(
        "--data-category",
        required=True,
        help="Dataset category to audit, such as admission_scores",
    )
    parser.add_argument(
        "--province",
        action="append",
        default=[],
        help="Expected province. Repeat for multiple provinces.",
    )
    parser.add_argument(
        "--year",
        action="append",
        default=[],
        type=int,
        help="Expected year. Repeat for multiple years.",
    )
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help="Warn when matching sources are not reviewed or approved.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return exit code 1 when warnings are present.",
    )
    parser.add_argument(
        "--audit-output",
        help="Optional path to write the source audit JSON for review",
    )
    args = parser.parse_args(argv)

    try:
        registry = SourceRegistry.from_json_file(Path(args.registry))
        audit = registry.audit_scope(
            data_category=args.data_category,
            expected_provinces=args.province,
            expected_years=args.year,
            require_reviewed=args.require_reviewed,
        ).to_dict()
        if args.audit_output:
            _write_json(Path(args.audit_output), audit)
    except (json.JSONDecodeError, OSError, TypeError, ValueError, ValidationError) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return _exit_code(audit, fail_on_warning=args.fail_on_warning)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _exit_code(audit: dict, *, fail_on_warning: bool) -> int:
    issues = audit.get("issues") or []
    has_error = any(issue.get("severity") == "error" for issue in issues)
    has_warning = any(issue.get("severity") == "warning" for issue in issues)
    if has_error or (fail_on_warning and has_warning):
        return 1
    return 0


def _error_payload(exc: Exception) -> dict[str, str]:
    return {
        "status": "error",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


if __name__ == "__main__":
    raise SystemExit(main())
