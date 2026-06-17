from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.real_data.source_registry import (
    HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
    SHANDONG_2025_REGULAR_BATCH_1_PAGE,
    SourcePage,
    SourceSnapshot,
    build_manual_snapshot,
    build_snapshot,
    get_source_page,
    sha256_bytes,
)


def test_shandong_pilot_source_page_is_registered_official_metadata():
    source = get_source_page("sd-2025-regular-batch-1-page")

    assert source == SHANDONG_2025_REGULAR_BATCH_1_PAGE
    assert source.source_name == "山东省教育招生考试院"
    assert source.source_type == "official_exam_authority"
    assert source.province == "山东"
    assert source.year == 2025
    assert source.published_at.isoformat() == "2025-07-19"
    assert source.source_url == "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996"
    assert source.attachments[0].url == (
        "https://www.sdzk.cn/Floadup/file/20250719/6388855130412530367357143.xls"
    )


def test_henan_candidate_source_page_is_registered_without_automatic_snapshot_attachment():
    source = get_source_page("ha-2025-undergrad-parallel-page")

    assert source == HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    assert source.source_name == "河南省教育考试院"
    assert source.source_type == "official_exam_authority"
    assert source.province == "河南"
    assert source.year == 2025
    assert source.published_at.isoformat() == "2025-12-07"
    assert source.document_title == "河南省2025年普通高招本科院校平行投档分数线"
    assert source.source_url == "https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html"
    assert source.attachments == ()


def test_source_page_rejects_missing_required_authority_fields():
    with pytest.raises(ValidationError) as exc_info:
        SourcePage.model_validate(
            {
                "source_page_id": "bad",
                "source_name": "",
                "source_type": "official_exam_authority",
                "province": "山东",
                "year": 2025,
                "document_title": "山东投档表",
                "source_url": "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
                "authority_note": "",
            }
        )

    error_text = str(exc_info.value)
    assert "source_name" in error_text
    assert "authority_note" in error_text


def test_source_page_rejects_non_official_attachment_host():
    with pytest.raises(ValidationError, match="attachment host must match"):
        SourcePage.model_validate(
            {
                "source_page_id": "bad-host",
                "source_name": "山东省教育招生考试院",
                "source_type": "official_exam_authority",
                "province": "山东",
                "year": 2025,
                "document_title": "山东投档表",
                "source_url": "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
                "authority_note": "官网发布",
                "attachments": [
                    {
                        "label": "投档表",
                        "file_name": "投档表.xls",
                        "url": "https://example.com/file.xls",
                        "raw_format": "xls",
                    }
                ],
            }
        )


def test_build_snapshot_requires_hash_and_timezone():
    source = SHANDONG_2025_REGULAR_BATCH_1_PAGE
    attachment = source.attachments[0]
    digest = sha256_bytes(b"pilot snapshot bytes")
    captured_at = datetime(2026, 6, 8, 15, 0, tzinfo=UTC)

    snapshot = build_snapshot(
        source_page=source,
        attachment=attachment,
        raw_file_sha256=digest,
        captured_at=captured_at,
        operator="codex",
    )

    assert snapshot.source_page_id == source.source_page_id
    assert snapshot.snapshot_id == "sd-2025-regular-batch-1-page-2026-06-08"
    assert snapshot.raw_file_sha256 == digest
    assert snapshot.raw_file_url == attachment.url


def test_build_manual_snapshot_supports_reviewed_dynamic_source_views():
    source = HENAN_2025_UNDERGRAD_PARALLEL_PAGE
    digest = sha256_bytes(b"reviewed henan physical table sample")
    captured_at = datetime(2026, 6, 9, 16, 45, tzinfo=UTC)

    snapshot = build_manual_snapshot(
        source_page=source,
        raw_file_name="henan-2025-undergrad-physical-sample.html",
        raw_file_url=(
            "https://datacenter.haeea.cn/PagePZQuery/ShowPZTDTJ.aspx?"
            "yearTip=2025&pc=1&kl=5"
        ),
        raw_file_sha256=digest,
        captured_at=captured_at,
        operator="codex",
        snapshot_id="ha-2025-undergrad-physical-reviewed-sample",
    )

    assert snapshot.source_batch_id == "河南-2025-manual"
    assert snapshot.source_page_id == source.source_page_id
    assert snapshot.snapshot_id == "ha-2025-undergrad-physical-reviewed-sample"
    assert snapshot.raw_file_name == "henan-2025-undergrad-physical-sample.html"
    assert snapshot.raw_file_sha256 == digest
    assert snapshot.captured_at == captured_at


@pytest.mark.parametrize("bad_hash", ["", "abc", "g" * 64])
def test_snapshot_rejects_invalid_sha256(bad_hash: str):
    with pytest.raises(ValidationError, match="raw_file_sha256"):
        SourceSnapshot.model_validate(
            {
                "source_batch_id": "sd-2025-xls",
                "source_page_id": "sd-2025-regular-batch-1-page",
                "snapshot_id": "snapshot",
                "captured_at": datetime(2026, 6, 8, 15, 0, tzinfo=UTC),
                "raw_file_name": "投档表.xls",
                "raw_file_url": (
                    "https://www.sdzk.cn/Floadup/file/20250719/"
                    "6388855130412530367357143.xls"
                ),
                "raw_file_sha256": bad_hash,
                "operator": "codex",
            }
        )


def test_snapshot_rejects_naive_capture_time():
    with pytest.raises(ValidationError, match="captured_at must include timezone"):
        SourceSnapshot.model_validate(
            {
                "source_batch_id": "sd-2025-xls",
                "source_page_id": "sd-2025-regular-batch-1-page",
                "snapshot_id": "snapshot",
                "captured_at": datetime(2026, 6, 8, 15, 0),
                "raw_file_name": "投档表.xls",
                "raw_file_url": (
                    "https://www.sdzk.cn/Floadup/file/20250719/"
                    "6388855130412530367357143.xls"
                ),
                "raw_file_sha256": "a" * 64,
                "operator": "codex",
            }
        )
