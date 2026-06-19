"""Tool response source metadata tests."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.data_pipeline.lineage import (
    build_answer_source_policy,
    create_lineage_record,
    upsert_snapshot,
    upsert_source,
)
from backend.data_pipeline.parsers import ManualSampleParser
from backend.data_pipeline.raw_store.manifest import ManifestFile, RawSnapshotManifest
from backend.data_pipeline.sources.registry import DataSource, SourceCoverage
from backend.database import Base
from backend.tools.definitions import _attach_sources_to_items
from backend.tools.definitions import _summarize_result_sources
from backend.tools.definitions import _unsupported_source_summary


def make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'tool_sources.db'}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestSession()


def make_source(review_status: str = "candidate") -> DataSource:
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
        review_status=review_status,
    )


def make_manifest(dataset: str = "admission_scores") -> RawSnapshotManifest:
    return RawSnapshotManifest(
        snapshot_id=f"sd_{dataset}_2025_001",
        source_id="sd_exam_authority",
        dataset=dataset,
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
            "source_record_ref": "manual_row=1",
        }
    ]
    return ManualSampleParser().parse(rows, make_manifest())[0]


def make_plan_candidate():
    rows = [
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
            "source_record_ref": "manual_row=2",
        }
    ]
    return ManualSampleParser().parse(rows, make_manifest("enrollment_plans"))[0]


def test_attach_sources_to_items_preserves_fields_and_adds_sources(tmp_path):
    with make_session(tmp_path) as db:
        upsert_source(db, make_source())
        upsert_snapshot(db, make_manifest())
        create_lineage_record(
            db,
            make_candidate(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            entity_id=101,
        )
        db.commit()

        items = [
            {"id": 101, "school_name": "山东大学", "min_score": 620},
            {"id": 102, "school_name": "未知大学", "min_score": 500},
        ]

        enriched = _attach_sources_to_items(db, items, "admission_score")

        assert enriched[0]["school_name"] == "山东大学"
        assert enriched[0]["min_score"] == 620
        assert enriched[0]["sources"][0]["source_id"] == "sd_exam_authority"
        assert enriched[0]["sources"][0]["source_type"] == (
            "provincial_exam_authority"
        )
        assert enriched[0]["sources"][0]["published_year"] == 2025
        assert enriched[0]["sources"][0]["confidence"] == 0.95
        assert enriched[0]["sources"][0]["trust_score"] == 1.0
        assert enriched[0]["sources"][0]["review_status"] == "candidate"
        assert enriched[0]["source_summary"] == {
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": True,
            "source_metadata_complete": True,
            "best_confidence": 0.95,
            "best_trust_score": 1.0,
            "freshness": "current",
            "review_statuses": ["candidate"],
        }
        assert enriched[1]["sources"] == []
        assert enriched[1]["source_summary"]["citation_ready"] is False
        assert enriched[1]["source_summary"]["needs_caution"] is True
        assert _summarize_result_sources(enriched) == {
            "item_count": 2,
            "items_with_sources": 1,
            "items_needing_caution": 2,
            "source_count": 1,
            "citation_ready": False,
            "needs_caution": True,
            "source_metadata_complete": False,
        }
        assert build_answer_source_policy(_summarize_result_sources(enriched)) == {
            "answer_mode": "unsupported",
            "citation_ready": False,
            "requires_citation": False,
            "requires_caution": True,
            "allowed_default_answer": False,
            "reasons": [
                "source_metadata_incomplete",
                "partial_source_coverage",
                "source_caution_required",
            ],
        }
        assert "sources" not in items[0]
        assert "source_summary" not in items[0]


def test_attach_sources_to_items_supports_enrollment_plan_sources(tmp_path):
    with make_session(tmp_path) as db:
        upsert_source(db, make_source())
        upsert_snapshot(db, make_manifest("enrollment_plans"))
        create_lineage_record(
            db,
            make_plan_candidate(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            entity_id=201,
        )
        db.commit()

        items = [
            {
                "id": 201,
                "school_name": "山东大学",
                "major_name": "计算机科学与技术",
                "plan_count": 20,
            }
        ]

        enriched = _attach_sources_to_items(db, items, "enrollment_plan")

        assert enriched[0]["plan_count"] == 20
        assert enriched[0]["sources"][0]["source_record_ref"] == "manual_row=2"
        assert enriched[0]["sources"][0]["quality_status"] == "passed"
        assert enriched[0]["sources"][0]["license_note"] == (
            "Official public source; review citation requirements."
        )
        assert enriched[0]["source_summary"]["source_count"] == 1
        assert _summarize_result_sources(enriched) == {
            "item_count": 1,
            "items_with_sources": 1,
            "items_needing_caution": 1,
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": True,
            "source_metadata_complete": True,
        }
        assert build_answer_source_policy(_summarize_result_sources(enriched)) == {
            "answer_mode": "citeable_with_caution",
            "citation_ready": True,
            "requires_citation": True,
            "requires_caution": True,
            "allowed_default_answer": False,
            "reasons": ["source_caution_required"],
        }


def test_approved_source_summary_is_citeable_without_caution(tmp_path):
    with make_session(tmp_path) as db:
        upsert_source(db, make_source(review_status="approved"))
        upsert_snapshot(db, make_manifest())
        create_lineage_record(
            db,
            make_candidate(),
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            entity_id=301,
        )
        db.commit()

        enriched = _attach_sources_to_items(
            db,
            [{"id": 301, "school_name": "山东大学", "min_score": 620}],
            "admission_score",
        )
        summary = _summarize_result_sources(enriched)

        assert enriched[0]["source_summary"]["review_statuses"] == ["approved"]
        assert enriched[0]["source_summary"]["needs_caution"] is False
        assert summary == {
            "item_count": 1,
            "items_with_sources": 1,
            "items_needing_caution": 0,
            "source_count": 1,
            "citation_ready": True,
            "needs_caution": False,
            "source_metadata_complete": True,
        }
        assert build_answer_source_policy(summary) == {
            "answer_mode": "citeable",
            "citation_ready": True,
            "requires_citation": True,
            "requires_caution": False,
            "allowed_default_answer": True,
            "reasons": [],
        }


def test_unsupported_source_summary_marks_legacy_results_unciteable():
    summary = _unsupported_source_summary(2)

    assert summary == {
        "item_count": 2,
        "items_with_sources": 0,
        "items_needing_caution": 2,
        "source_count": 0,
        "citation_ready": False,
        "needs_caution": True,
        "source_metadata_complete": False,
        "source_status": "legacy_untraced",
    }
    assert build_answer_source_policy(summary) == {
        "answer_mode": "unsupported",
        "citation_ready": False,
        "requires_citation": False,
        "requires_caution": True,
        "allowed_default_answer": False,
        "reasons": [
            "legacy_untraced_tool",
            "source_metadata_incomplete",
            "no_sources",
            "partial_source_coverage",
            "source_caution_required",
        ],
    }
