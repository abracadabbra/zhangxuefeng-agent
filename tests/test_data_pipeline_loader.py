"""Canonical loader tests for quality-gated pilot candidates."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.data_pipeline.lineage import upsert_snapshot, upsert_source
from backend.data_pipeline.loaders import (
    load_candidate,
    load_candidates,
    load_candidates_after_audit,
    load_candidates_after_artifact_manifest,
)
from backend.data_pipeline.pilots import PilotLoadNotReadyError, run_manual_pilot
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage
from backend.database import Base
from backend.models.admission_score import AdmissionScore
from backend.models.data_lineage import DataLineageRecord
from backend.models.enrollment_plan import EnrollmentPlan
from backend.models.major import Major
from backend.models.school import School


def make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'loader.db'}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestSession()


def seed_reference_data(db):
    school = School(
        name="山东大学",
        province="山东",
        city="济南",
        level="985",
        school_type="综合",
        is_985=1,
        is_211=1,
        is_double_first_class=1,
    )
    major = Major(
        name="计算机科学与技术",
        category="工学",
        sub_category="计算机类",
    )
    db.add_all([school, major])
    db.flush()


def make_source() -> DataSource:
    return DataSource(
        source_id="sd_exam_authority",
        name="Shandong Education Admissions Examination Institute",
        source_type="provincial_exam_authority",
        homepage_url="https://www.sdzk.cn/default.aspx",
        data_categories=["admission_scores", "enrollment_plans"],
        coverage=SourceCoverage(provinces=["山东"], years=[2025]),
        trust_score=1.0,
        update_frequency="annual",
        collection_method="manual_download",
        license_note="Official public source; review citation requirements.",
    )


def make_manifest() -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id="sd_pilot_2025_001",
        source_id="sd_exam_authority",
        dataset="admission_scores",
        source_url="https://example.gov.cn/manual-sample.csv",
        published_year=2025,
        collected_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        collector="manual",
        collector_version="0.1.0",
        files=[
            ManifestFile(
                path="files/manual-sample.csv",
                sha256="a" * 64,
                content_type="text/csv",
            )
        ],
        license_note="Test fixture only.",
    )


def make_candidates():
    rows = [
        {
            "dataset": "admission_scores",
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        },
        {
            "dataset": "enrollment_plans",
            "school_name": "山东大学",
            "major_name": "计算机科学与技术",
            "province": "山东",
            "year": 2025,
            "plan_count": 20,
            "subject_requirement": "物理+化学",
            "batch": "本科批",
            "duration": 4,
            "tuition": 6600,
        },
    ]
    return ManualSampleParser().parse(rows, make_manifest())


def prepare_lineage_dependencies(db):
    upsert_source(db, make_source())
    upsert_snapshot(db, make_manifest())


def test_loader_creates_canonical_rows_and_lineage_records(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)

        results = load_candidates(
            db,
            make_candidates(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
        db.commit()

        assert [result.created for result in results] == [True, True]
        assert db.query(AdmissionScore).one().min_score == 620
        assert db.query(EnrollmentPlan).one().plan_count == 20
        assert db.query(DataLineageRecord).count() == 2


def test_loader_upserts_existing_admission_score(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)
        candidate = make_candidates()[0]

        first = load_candidate(
            db,
            candidate,
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
        candidate.values["min_score"] = 625
        second = load_candidate(
            db,
            candidate,
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
        db.commit()

        assert first.created is True
        assert second.created is False
        assert first.entity_id == second.entity_id
        assert db.query(AdmissionScore).one().min_score == 625
        assert db.query(DataLineageRecord).count() == 2


def test_loader_rejects_unknown_school(tmp_path):
    with make_session(tmp_path) as db:
        prepare_lineage_dependencies(db)

        with pytest.raises(ValueError, match="unknown school_name"):
            load_candidate(
                db,
                make_candidates()[0],
                parser_name="ManualSampleParser",
                parser_version="0.1.0",
            )


def test_load_candidates_after_audit_loads_only_when_ready(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)
        candidates = make_candidates()
        audit = run_manual_pilot(
            [
                {
                    "dataset": "admission_scores",
                    "school_name": "山东大学",
                    "major_name": None,
                    "province": "山东",
                    "year": 2025,
                    "batch": "本科批",
                    "subject_type": "综合",
                    "min_score": 620,
                }
            ],
            make_manifest(),
            source=make_source(),
        ).to_audit_dict()

        results = load_candidates_after_audit(
            db,
            [candidates[0]],
            audit,
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
        db.commit()

        assert [result.created for result in results] == [True]
        assert db.query(AdmissionScore).one().min_score == 620
        assert db.query(DataLineageRecord).count() == 1


def test_load_candidates_after_audit_blocks_failed_audit(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)
        audit = {
            "load_ready": False,
            "blockers": ["quality_error:value_out_of_range"],
        }

        with pytest.raises(PilotLoadNotReadyError):
            load_candidates_after_audit(
                db,
                [make_candidates()[0]],
                audit,
                parser_name="ManualSampleParser",
                parser_version="0.1.0",
            )

        assert db.query(AdmissionScore).count() == 0
        assert db.query(DataLineageRecord).count() == 0


def test_load_candidates_after_audit_blocks_warning_review_audit(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)
        audit = {
            "load_ready": True,
            "blockers": [],
            "review_status": "needs_warning_review",
            "review_notes": ["warning requires review: stale_data"],
        }

        with pytest.raises(PilotLoadNotReadyError, match="needs_warning_review"):
            load_candidates_after_audit(
                db,
                [make_candidates()[0]],
                audit,
                parser_name="ManualSampleParser",
                parser_version="0.1.0",
            )

        assert db.query(AdmissionScore).count() == 0
        assert db.query(DataLineageRecord).count() == 0


def test_load_candidates_after_artifact_manifest_requires_ready_manifest(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)

        with pytest.raises(PilotLoadNotReadyError, match="Resolve artifact scope"):
            load_candidates_after_artifact_manifest(
                db,
                [make_candidates()[0]],
                {
                    "ready_for_loader_execution": False,
                    "required_reviews": ["Resolve artifact scope issues."],
                    "intake_review_issues": [
                        "missing intake readiness review"
                    ],
                    "artifact_scope_issues": [
                        "source audit province is missing from dry-run coverage: 山东"
                    ],
                },
                parser_name="ManualSampleParser",
                parser_version="0.1.0",
            )

        assert db.query(AdmissionScore).count() == 0
        assert db.query(DataLineageRecord).count() == 0


def test_load_candidates_after_artifact_manifest_reports_intake_issues(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)

        with pytest.raises(PilotLoadNotReadyError, match="intake_review_issues"):
            load_candidates_after_artifact_manifest(
                db,
                [make_candidates()[0]],
                {
                    "ready_for_loader_execution": False,
                    "intake_review_issues": [
                        "missing intake readiness review"
                    ],
                },
                parser_name="ManualSampleParser",
                parser_version="0.1.0",
            )

        assert db.query(AdmissionScore).count() == 0
        assert db.query(DataLineageRecord).count() == 0


def test_load_candidates_after_artifact_manifest_loads_when_manifest_ready(tmp_path):
    with make_session(tmp_path) as db:
        seed_reference_data(db)
        prepare_lineage_dependencies(db)

        results = load_candidates_after_artifact_manifest(
            db,
            [make_candidates()[0]],
            {
                "ready_for_loader_execution": True,
                "required_reviews": [
                    "Provide a separate approved loader run command."
                ],
            },
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
        )
        db.commit()

        assert [result.created for result in results] == [True]
        assert db.query(AdmissionScore).one().min_score == 620
        assert db.query(DataLineageRecord).count() == 1
