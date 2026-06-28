"""Source metadata formatting tests."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.data_pipeline.lineage import (
    SourceMetadataConfig,
    create_lineage_record,
    get_sources_for_entity,
    summarize_sources,
    upsert_snapshot,
    upsert_source,
)
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage
from backend.database import Base


def make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lineage_sources.db'}",
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


def make_manifest(year: int = 2025) -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id=f"sd_scores_{year}_001",
        source_id="sd_exam_authority",
        dataset="admission_scores",
        source_url="https://example.gov.cn/manual-sample.csv",
        published_year=year,
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


def make_candidate(year: int = 2025):
    rows = [
        {
            "school_name": "山东大学",
            "major_name": None,
            "province": "山东",
            "year": year,
            "batch": "本科批",
            "subject_type": "综合",
            "min_score": 620,
            "source_record_ref": "manual_row=1",
        }
    ]
    return ManualSampleParser().parse(rows, make_manifest(year))[0]


def test_get_sources_for_entity_formats_agent_source_envelope(tmp_path):
    with make_session(tmp_path) as db:
        upsert_source(db, make_source())
        upsert_snapshot(db, make_manifest())
        create_lineage_record(
            db,
            make_candidate(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            entity_id=1,
        )
        db.commit()

        sources = get_sources_for_entity(
            db,
            "admission_score",
            1,
            SourceMetadataConfig(current_year=2026),
        )

        assert sources == [
            {
                "source_id": "sd_exam_authority",
                "name": "Shandong Education Admissions Examination Institute",
                "source_type": "provincial_exam_authority",
                "source_url": "https://example.gov.cn/manual-sample.csv",
                "published_year": 2025,
                "snapshot_id": "sd_scores_2025_001",
                "source_record_ref": "manual_row=1",
                "confidence": 0.95,
                "freshness": "current",
                "quality_status": "passed",
                "trust_score": 1.0,
                "review_status": "candidate",
                "license_note": (
                    "Official public source; review citation requirements."
                ),
            }
        ]


def test_get_sources_for_entity_marks_stale_and_expired_sources(tmp_path):
    with make_session(tmp_path) as db:
        upsert_source(db, make_source())
        upsert_snapshot(db, make_manifest(2023))
        create_lineage_record(
            db,
            make_candidate(2023),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="warning",
            entity_id=1,
        )
        db.commit()

        stale = get_sources_for_entity(
            db,
            "admission_score",
            1,
            SourceMetadataConfig(current_year=2026),
        )
        expired = get_sources_for_entity(
            db,
            "admission_score",
            1,
            SourceMetadataConfig(current_year=2028),
        )

        assert stale[0]["freshness"] == "stale"
        assert expired[0]["freshness"] == "expired"


def test_summarize_sources_marks_citation_ready_and_caution():
    summary = summarize_sources(
        [
            {
                "source_id": "src-1",
                "snapshot_id": 10,
                "published_year": 2024,
                "confidence": 0.95,
                "trust_score": 1.0,
                "freshness": "current",
                "review_status": "reviewed",
            }
        ]
    )

    assert summary == {
        "source_count": 1,
        "citation_ready": True,
        "needs_caution": False,
        "source_metadata_complete": True,
        "best_confidence": 0.95,
        "best_trust_score": 1.0,
        "freshness": "current",
        "review_statuses": ["reviewed"],
    }


def test_summarize_sources_marks_missing_sources_as_not_citation_ready():
    assert summarize_sources([]) == {
        "source_count": 0,
        "citation_ready": False,
        "needs_caution": True,
        "source_metadata_complete": False,
        "best_confidence": None,
        "best_trust_score": None,
        "freshness": "unknown",
        "review_statuses": [],
    }


def test_summarize_sources_marks_incomplete_metadata_as_caution():
    summary = summarize_sources(
        [
            {
                "source_id": "src-1",
                "snapshot_id": 10,
                "published_year": 2024,
                "freshness": "current",
                "review_status": "reviewed",
            }
        ]
    )

    assert summary["citation_ready"] is False
    assert summary["needs_caution"] is True
    assert summary["best_confidence"] is None
    assert summary["best_trust_score"] is None
