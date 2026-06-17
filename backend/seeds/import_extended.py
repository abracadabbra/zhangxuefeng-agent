"""Compatibility wrapper for the extended seed-data import command.

Usage:
    python -m backend.seeds.import_extended
"""

from __future__ import annotations

import json
from typing import Any

from backend.seeds import import_cli


def run_extended_import() -> import_cli.ImportReport:
    """Run the extended seed-data import through the unified CLI implementation."""
    report = import_cli.run_import("extended")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return report


def load_json(filename: str) -> list[dict[str, Any]]:
    """Backward-compatible JSON loader used by older scripts/tests."""
    return import_cli.load_json_file(import_cli.DATA_DIR / filename)


if __name__ == "__main__":
    run_extended_import()
