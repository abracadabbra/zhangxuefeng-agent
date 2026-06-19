"""Data lineage ORM model tests."""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.data_lineage import DataLineageRecord, DataSnapshot, DataSourceRecord


def test_data_lineage_models_persist_source_snapshot_and_record(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lineage.db'}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestSession() as db:
        source = DataSourceRecord(
            source_id="sd_exam_authority",
            name="Shandong Education Admissions Examination Institute",
            source_type="provincial_exam_authority",
            homepage_url="https://www.sdzk.cn/default.aspx",
            data_categories='["admission_scores"]',
            coverage='{"provinces":["山东"],"years":[2025]}',
            trust_score=1.0,
            update_frequency="annual",
            collection_method="manual_download",
            license_note="Official public source; review citation requirements.",
            review_status="candidate",
        )
        snapshot = DataSnapshot(
            snapshot_id="sd_scores_2025_001",
            source_id="sd_exam_authority",
            dataset="admission_scores",
            source_url="https://example.gov.cn/manual-sample.csv",
            published_year=2025,
            collected_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
            collector="manual",
            collector_version="0.1.0",
            files='[{"path":"files/manual-sample.csv"}]',
            license_note="Test fixture only.",
            checksum_status="verified",
        )
        lineage = DataLineageRecord(
            entity_type="admission_score",
            entity_id=1,
            natural_key_json='{"school_name":"山东大学","province":"山东","year":2025}',
            snapshot_id="sd_scores_2025_001",
            source_record_ref="manual_row=1",
            parser_name="ManualSampleParser",
            parser_version="0.1.0",
            quality_status="passed",
            confidence=0.95,
        )

        db.add_all([source, snapshot, lineage])
        db.commit()

        saved_source = db.query(DataSourceRecord).one()
        saved_snapshot = db.query(DataSnapshot).one()
        saved_lineage = db.query(DataLineageRecord).one()

        assert saved_source.snapshots == [saved_snapshot]
        assert saved_snapshot.lineage_records == [saved_lineage]
        assert saved_lineage.snapshot.source.source_id == "sd_exam_authority"
