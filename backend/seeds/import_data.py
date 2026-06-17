"""Compatibility wrapper for the basic seed-data import command.

Usage:
    python -m backend.seeds.import_data
"""

from __future__ import annotations

import json
from typing import Any

from backend.seeds import import_cli


def run_import() -> import_cli.ImportReport:
    """Run the basic seed-data import through the unified CLI implementation."""
    report = import_cli.run_import("basic")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return report


def load_json(filename: str) -> list[dict[str, Any]]:
    """Backward-compatible JSON loader used by older scripts/tests."""
    return import_cli.load_json_file(import_cli.DATA_DIR / filename)


if __name__ == "__main__":
    run_import()
