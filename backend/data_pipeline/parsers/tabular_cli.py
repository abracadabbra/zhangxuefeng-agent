"""No-write CLI for reviewed tabular pilot rows."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.data_pipeline.parsers.tabular_samples import normalize_tabular_rows


def main(argv: list[str] | None = None) -> int:
    """Normalize a reviewed CSV worksheet into a rows bundle."""
    parser = argparse.ArgumentParser(
        description="Normalize reviewed tabular rows into a pilot rows bundle",
    )
    parser.add_argument("csv_path", help="Path to a reviewed local CSV file")
    parser.add_argument(
        "--dataset",
        help="Optional dataset to apply when rows do not include dataset",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the rows bundle JSON",
    )
    args = parser.parse_args(argv)

    try:
        rows = _read_csv(Path(args.csv_path))
        payload = {
            "rows": normalize_tabular_rows(rows, dataset=args.dataset),
        }
        if args.output:
            _write_json(Path(args.output), payload)
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
