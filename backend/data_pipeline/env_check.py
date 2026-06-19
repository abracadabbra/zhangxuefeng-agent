"""No-write environment checks for the real-data MVP pipeline."""

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleCheck:
    """Result for one importable module check."""

    module: str
    required_for: str
    installed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "module": self.module,
            "required_for": self.required_for,
            "installed": self.installed,
        }


RUNTIME_MODULES = {
    "pydantic": "contracts, parsers, quality gate, dry-run CLI",
    "sqlalchemy": "canonical loader and lineage database access",
}
DEV_MODULES = {
    "pytest": "test suite",
}
MIN_PYTHON = (3, 11)


def build_env_report(*, include_dev: bool = True) -> dict[str, object]:
    """Build a JSON-ready dependency report without importing target modules."""
    python_version = _python_version()
    python_version_ok = _python_version_tuple() >= MIN_PYTHON
    checks = [
        _check_module(module, required_for)
        for module, required_for in RUNTIME_MODULES.items()
    ]
    if include_dev:
        checks.extend(
            _check_module(module, required_for)
            for module, required_for in DEV_MODULES.items()
        )

    missing = [check for check in checks if not check.installed]
    missing_reasons = [check.module for check in missing]
    if not python_version_ok:
        missing_reasons.insert(0, "python")

    runtime_modules_ready = not any(
        check.module in RUNTIME_MODULES and not check.installed
        for check in checks
    )
    tests_ready = include_dev and not any(
        check.module in DEV_MODULES and not check.installed
        for check in checks
    )
    return {
        "status": "ok" if not missing_reasons else "missing_dependencies",
        "python_version": python_version,
        "required_python": ">=3.11",
        "python_version_ok": python_version_ok,
        "ready_for_cli_runtime": python_version_ok and runtime_modules_ready,
        "ready_for_tests": python_version_ok and tests_ready,
        "checks": [check.to_dict() for check in checks],
        "missing_modules": missing_reasons,
        "install_hint": _install_hint(missing_reasons, include_dev=include_dev),
    }


def main(argv: list[str] | None = None) -> int:
    """Print a no-write environment report as JSON."""
    parser = argparse.ArgumentParser(description="Check real-data MVP dependencies")
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help="Skip dev/test dependency checks.",
    )
    args = parser.parse_args(argv)

    report = build_env_report(include_dev=not args.runtime_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


def _check_module(module: str, required_for: str) -> ModuleCheck:
    return ModuleCheck(
        module=module,
        required_for=required_for,
        installed=importlib.util.find_spec(module) is not None,
    )


def _python_version() -> str:
    major, minor, micro = _python_version_tuple()
    return f"{major}.{minor}.{micro}"


def _python_version_tuple() -> tuple[int, int, int]:
    version_info = sys.version_info
    return (
        int(version_info[0]),
        int(version_info[1]),
        int(version_info[2]),
    )


def _install_hint(missing: list[str], *, include_dev: bool) -> str:
    if not missing:
        return ""
    if "python" in missing and len(missing) == 1:
        return "Use Python 3.11 or newer."
    install_command = 'pip install -e ".[dev]"' if include_dev else 'pip install -e "."'
    if "python" in missing:
        return f"Use Python 3.11 or newer, then run: {install_command}"
    return install_command


if __name__ == "__main__":
    raise SystemExit(main())
