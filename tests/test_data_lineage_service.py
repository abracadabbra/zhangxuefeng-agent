"""Data lineage service tests."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.data_pipeline.lineage import (
    create_lineage_record,
    get_lineage_for_entity,
    get_lineage_for_snapshot,
    get_snapshot,
    get_source,
    upsert_snapshot,
    upsert_source,
)
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage
from backend.database import Base


def make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lineage_service.db'}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestSession()


def make_source() -> DataSource:
    return DataSource(
        source_id="sd_exam_authority",
        name="Shandong Education Admissions Examination Institute",
        source_type="provincial_exam_authority",
        homepage_url="https://www.sdzk.cn/default.aspx",
        data_categories=["admission_scores"],
        coverage=SourceCoverage(provinces=["山东"], years=[2025]),
        trust_score=1.0,
        update_frequency="annual",
        collection_method="manual_download",
        license_note="Official public source; review citation requirements.",
    )


def make_manifest() -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id="sd_scores_2025_001",
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


def make_candidate():
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": 2025,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "min_rank": 12000,
        }
    ]
    return ManualSampleParser().parse(rows, make_manifest())[0]


def test_lineage_service_persists_source_snapshot_and_candidate_lineage(tmp_path):
    with make_session(tmp_path) as db:
        source_record = upsert_source(db, make_source())
        snapshot = upsert_snapshot(db, make_manifest())
        lineage = create_lineage_record(
            db,
            make_candidate(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            entity_id=1,
        )
        db.commit()

        assert get_source(db, "sd_exam_authority") == source_record
        assert get_snapshot(db, "sd_scores_2025_001") == snapshot
        assert get_lineage_for_snapshot(db, "sd_scores_2025_001") == [lineage]
        assert get_lineage_for_entity(db, "admission_score", 1) == [lineage]
        assert lineage.snapshot.source.source_id == "sd_exam_authority"


def test_lineage_service_upserts_existing_source_and_snapshot(tmp_path):
    with make_session(tmp_path) as db:
        source = make_source()
        upsert_source(db, source)
        source.name = "Updated Source Name"
        updated_source = upsert_source(db, source)

        manifest = make_manifest()
        upsert_snapshot(db, manifest)
        manifest.license_note = "Updated license note."
        updated_snapshot = upsert_snapshot(db, manifest)
        db.commit()

        assert updated_source.id == 1
        assert updated_source.name == "Updated Source Name"
        assert updated_snapshot.id == 1
        assert updated_snapshot.license_note == "Updated license note."
