"""Environment check tests for the real-data MVP pipeline."""

from backend.data_pipeline import env_check


def test_build_env_report_marks_ready_when_modules_exist(monkeypatch):
    monkeypatch.setattr(env_check.importlib.util, "find_spec", lambda module: object())

    report = env_check.build_env_report()

    assert report["status"] == "ok"
    assert report["ready_for_cli_runtime"] is True
    assert report["ready_for_tests"] is True
    assert report["missing_modules"] == []
    assert report["install_hint"] == ""


def test_build_env_report_reports_missing_runtime_and_dev_modules(monkeypatch):
    installed = {"sqlalchemy"}

    monkeypatch.setattr(
        env_check.importlib.util,
        "find_spec",
        lambda module: object() if module in installed else None,
    )

    report = env_check.build_env_report()

    assert report["status"] == "missing_dependencies"
    assert report["ready_for_cli_runtime"] is False
    assert report["ready_for_tests"] is False
    assert report["missing_modules"] == ["pydantic", "pytest"]
    assert report["install_hint"] == 'pip install -e ".[dev]"'


def test_build_env_report_can_skip_dev_checks(monkeypatch):
    installed = {"pydantic", "sqlalchemy"}

    monkeypatch.setattr(
        env_check.importlib.util,
        "find_spec",
        lambda module: object() if module in installed else None,
    )

    report = env_check.build_env_report(include_dev=False)

    assert report["status"] == "ok"
    assert report["ready_for_cli_runtime"] is True
    assert report["ready_for_tests"] is False
    assert report["missing_modules"] == []


def test_build_env_report_runtime_only_uses_runtime_install_hint(monkeypatch):
    monkeypatch.setattr(env_check.importlib.util, "find_spec", lambda module: None)

    report = env_check.build_env_report(include_dev=False)

    assert report["status"] == "missing_dependencies"
    assert report["missing_modules"] == ["pydantic", "sqlalchemy"]
    assert report["install_hint"] == 'pip install -e "."'


def test_build_env_report_requires_python_311_or_newer(monkeypatch):
    monkeypatch.setattr(env_check.importlib.util, "find_spec", lambda module: object())
    monkeypatch.setattr(env_check.sys, "version_info", (3, 10, 12))

    report = env_check.build_env_report()

    assert report["status"] == "missing_dependencies"
    assert report["python_version"] == "3.10.12"
    assert report["required_python"] == ">=3.11"
    assert report["python_version_ok"] is False
    assert report["ready_for_cli_runtime"] is False
    assert report["ready_for_tests"] is False
    assert report["missing_modules"] == ["python"]
    assert report["install_hint"] == "Use Python 3.11 or newer."


def test_env_check_cli_returns_nonzero_for_missing_modules(monkeypatch, capsys):
    monkeypatch.setattr(env_check.importlib.util, "find_spec", lambda module: None)

    exit_code = env_check.main([])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert '"status": "missing_dependencies"' in output
    assert '"pydantic"' in output
