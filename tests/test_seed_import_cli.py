import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import AdmissionScore, EnrollmentPlan, Major, School, SubjectRanking
from backend.seeds import import_cli, import_data, import_extended, import_full_data


@pytest.fixture()
def seed_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(import_cli, "engine", engine)
    monkeypatch.setattr(import_cli, "SessionLocal", Session)
    return Session


def _write_json(path: Path, name: str, data: list[dict]) -> None:
    path.joinpath(name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _seed_files(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "seed_schools.json",
        [
            {
                "name": "测试大学",
                "province": "北京",
                "city": "北京",
                "level": "普通",
                "school_type": "综合",
            }
        ],
    )
    _write_json(
        tmp_path,
        "seed_majors.json",
        [{"name": "测试专业", "category": "工学", "avg_salary": 12000}],
    )
    _write_json(
        tmp_path,
        "seed_scores_all.json",
        [
            {
                "school_name": "测试大学",
                "province": "北京",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 580,
            }
        ],
    )
    _write_json(
        tmp_path,
        "seed_plans.json",
        [
            {
                "school_name": "测试大学",
                "major_name": "测试专业",
                "province": "北京",
                "year": 2025,
                "plan_count": 12,
                "subject_requirement": "不限",
                "batch": "本科批",
            }
        ],
    )
    _write_json(
        tmp_path,
        "seed_subject_rankings.json",
        [
            {
                "school_name": "测试大学",
                "major_category": "工学",
                "ranking_source": "测试排名",
                "ranking_year": 2025,
                "grade": "A",
            }
        ],
    )


def test_dry_run_reports_without_writing(tmp_path, seed_db):
    _seed_files(tmp_path)

    report = import_cli.run_import("basic", dry_run=True, data_dir=tmp_path)

    assert report.schools.inserted == 1
    assert report.majors.inserted == 1
    assert report.scores.inserted == 1
    assert report.plans.inserted == 1
    assert report.rankings.inserted == 1
    with seed_db() as db:
        assert db.query(School).count() == 0
        assert db.query(Major).count() == 0
        assert db.query(AdmissionScore).count() == 0
        assert db.query(EnrollmentPlan).count() == 0
        assert db.query(SubjectRanking).count() == 0


def test_import_inserts_core_seed_data(tmp_path, seed_db):
    _seed_files(tmp_path)

    report = import_cli.run_import("basic", data_dir=tmp_path)

    assert report.schools.inserted == 1
    assert report.majors.inserted == 1
    assert report.scores.inserted == 1
    assert report.plans.inserted == 1
    assert report.rankings.inserted == 1
    with seed_db() as db:
        assert db.query(School).count() == 1
        assert db.query(Major).count() == 1
        assert db.query(AdmissionScore).count() == 1
        assert db.query(EnrollmentPlan).count() == 1
        assert db.query(SubjectRanking).count() == 1


def test_import_report_summary_totals_all_sections(tmp_path, seed_db):
    _seed_files(tmp_path)

    report = import_cli.run_import("basic", data_dir=tmp_path)

    assert report.summary() == {
        "loaded": 5,
        "valid": 5,
        "invalid": 0,
        "inserted": 5,
        "updated": 0,
        "skipped": 0,
        "error_count": 0,
        "has_errors": False,
    }
    assert report.to_dict()["summary"]["inserted"] == 5


def test_duplicate_policy_skip_and_update(tmp_path, seed_db):
    _seed_files(tmp_path)
    import_cli.run_import("basic", data_dir=tmp_path)

    skip_report = import_cli.run_import("basic", duplicate_policy="skip", data_dir=tmp_path)
    assert skip_report.schools.skipped == 1
    assert skip_report.majors.skipped == 1
    assert skip_report.scores.skipped == 1
    assert skip_report.plans.skipped == 1
    assert skip_report.rankings.skipped == 1

    _write_json(
        tmp_path,
        "seed_schools.json",
        [
            {
                "name": "测试大学",
                "province": "上海",
                "city": "上海",
                "level": "双一流",
                "school_type": "理工",
            }
        ],
    )
    update_report = import_cli.run_import("basic", duplicate_policy="update", data_dir=tmp_path)

    assert update_report.schools.updated == 1
    assert update_report.plans.updated == 1
    assert update_report.rankings.updated == 1
    with seed_db() as db:
        school = db.query(School).filter(School.name == "测试大学").one()
        assert school.province == "上海"
        assert school.level == "双一流"


def test_duplicate_policy_error_reports_invalid_rows(tmp_path, seed_db):
    _seed_files(tmp_path)
    import_cli.run_import("basic", data_dir=tmp_path)

    report = import_cli.run_import("basic", duplicate_policy="error", data_dir=tmp_path)

    assert report.schools.invalid == 1
    assert report.majors.invalid == 1
    assert report.scores.invalid == 1
    assert report.plans.invalid == 1
    assert report.rankings.invalid == 1
    assert "duplicate school" in report.schools.errors[0]
    with seed_db() as db:
        assert db.query(School).count() == 1
        assert db.query(Major).count() == 1
        assert db.query(AdmissionScore).count() == 1
        assert db.query(EnrollmentPlan).count() == 1
        assert db.query(SubjectRanking).count() == 1


def test_score_quality_validation_rejects_out_of_range_scores(tmp_path, seed_db):
    _seed_files(tmp_path)
    _write_json(
        tmp_path,
        "seed_scores_all.json",
        [
            {
                "school_name": "测试大学",
                "province": "北京",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 900,
            }
        ],
    )

    report = import_cli.run_import("basic", data_dir=tmp_path)

    assert report.scores.invalid == 1
    assert report.scores.inserted == 0
    assert "min_score out of range" in report.scores.errors[0]
    with seed_db() as db:
        assert db.query(AdmissionScore).count() == 0


def test_main_returns_failure_when_report_has_reference_errors(tmp_path, seed_db):
    _seed_files(tmp_path)
    _write_json(
        tmp_path,
        "seed_scores_all.json",
        [
            {
                "school_name": "不存在大学",
                "province": "北京",
                "year": 2025,
                "batch": "本科批",
                "subject_type": "综合",
                "min_score": 580,
            }
        ],
    )
    report_path = tmp_path / "report.json"

    exit_code = import_cli.main(
        [
            "--dataset",
            "basic",
            "--data-dir",
            str(tmp_path),
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "school not found" in report["scores"]["errors"][0]


def test_write_report_writes_json_file(tmp_path):
    report = import_cli.ImportReport(
        dataset="basic",
        dry_run=True,
        duplicate_policy="skip",
        files={"schools": ["seed_schools.json"]},
    )
    report.schools.inserted = 1
    report_path = tmp_path / "report.json"

    import_cli.write_report(report, report_path)

    written_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert written_report["schools"]["inserted"] == 1
    assert written_report["summary"]["inserted"] == 1
    assert written_report["summary"]["has_errors"] is False


def test_main_returns_failure_when_report_has_invalid_rows(tmp_path, seed_db):
    _seed_files(tmp_path)
    import_cli.run_import("basic", data_dir=tmp_path)
    report_path = tmp_path / "report.json"

    exit_code = import_cli.main(
        [
            "--dataset",
            "basic",
            "--duplicate-policy",
            "error",
            "--data-dir",
            str(tmp_path),
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schools"]["invalid"] == 1


@pytest.mark.parametrize(
    ("module", "function_name", "dataset"),
    [
        (import_data, "run_import", "basic"),
        (import_full_data, "run_import", "full"),
        (import_extended, "run_extended_import", "extended"),
    ],
)
def test_legacy_import_entrypoints_delegate_to_unified_cli(
    monkeypatch,
    module,
    function_name,
    dataset,
):
    calls = []
    expected_report = import_cli.ImportReport(
        dataset=dataset,
        dry_run=False,
        duplicate_policy="skip",
        files={},
    )

    def fake_run_import(name):
        calls.append(name)
        return expected_report

    monkeypatch.setattr(module.import_cli, "run_import", fake_run_import)

    report = getattr(module, function_name)()

    assert calls == [dataset]
    assert report is expected_report
