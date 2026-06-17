"""Source and snapshot contracts for real admission data pilots."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from typing import Literal
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

SourceType = Literal["official_exam_authority", "authorized_partner"]

_SHA256_HEX_LENGTH = 64


class SourceAttachment(BaseModel):
    """A file linked from an official source page."""

    label: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    raw_format: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("attachment url must be absolute http(s)")
        return value


class SourcePage(BaseModel):
    """Official or authorized page that publishes real admission data."""

    source_page_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: SourceType
    province: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    document_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    published_at: date | None = None
    authority_note: str = Field(min_length=1)
    attachments: tuple[SourceAttachment, ...] = Field(default_factory=tuple)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source url must be absolute http(s)")
        return value

    @model_validator(mode="after")
    def validate_attachments(self) -> SourcePage:
        source_host = urlparse(self.source_url).netloc
        for attachment in self.attachments:
            if urlparse(attachment.url).netloc != source_host:
                raise ValueError("attachment host must match source page host")
        return self


class SourceSnapshot(BaseModel):
    """Captured raw file snapshot with enough metadata for row-level lineage."""

    source_batch_id: str = Field(min_length=1)
    source_page_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    captured_at: datetime
    raw_file_name: str = Field(min_length=1)
    raw_file_url: str = Field(min_length=1)
    raw_file_sha256: str = Field(min_length=_SHA256_HEX_LENGTH, max_length=_SHA256_HEX_LENGTH)
    operator: str = Field(min_length=1)

    @field_validator("raw_file_url")
    @classmethod
    def validate_raw_file_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("raw file url must be absolute http(s)")
        return value

    @field_validator("raw_file_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != _SHA256_HEX_LENGTH:
            raise ValueError("raw file sha256 must be 64 hex characters")
        try:
            int(normalized, 16)
        except ValueError as exc:
            raise ValueError("raw file sha256 must be 64 hex characters") from exc
        return normalized

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include timezone information")
        return value


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 hex digest for a raw snapshot payload."""

    return hashlib.sha256(data).hexdigest()


def utc_snapshot_time() -> datetime:
    """Return a timezone-aware timestamp for snapshot metadata."""

    return datetime.now(UTC)


SHANDONG_2025_REGULAR_BATCH_1_PAGE = SourcePage(
    source_page_id="sd-2025-regular-batch-1-page",
    source_name="山东省教育招生考试院",
    source_type="official_exam_authority",
    province="山东",
    year=2025,
    document_title="山东省2025年普通类常规批第1次志愿投档情况表",
    source_url="https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
    published_at=date(2025, 7, 19),
    authority_note="山东省省级教育招生考试机构官网发布。",
    attachments=(
        SourceAttachment(
            label="山东省2025年普通类常规批第1次志愿投档情况表.xls",
            file_name="山东省2025年普通类常规批第1次志愿投档情况表.xls",
            url=urljoin(
                "https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996",
                "/Floadup/file/20250719/6388855130412530367357143.xls",
            ),
            raw_format="xls",
        ),
    ),
)


HENAN_2025_UNDERGRAD_PARALLEL_PAGE = SourcePage(
    source_page_id="ha-2025-undergrad-parallel-page",
    source_name="河南省教育考试院",
    source_type="official_exam_authority",
    province="河南",
    year=2025,
    document_title="河南省2025年普通高招本科院校平行投档分数线",
    source_url="https://gaokao.haedu.cn/517/518/519/2025/1207/150720.html",
    published_at=date(2025, 12, 7),
    authority_note="河南省教育考试院通过河南高考信息网发布，页面链接至物理类/历史类本科批平行投档分数线查询入口。",
)


SOURCE_PAGES: dict[str, SourcePage] = {
    HENAN_2025_UNDERGRAD_PARALLEL_PAGE.source_page_id: HENAN_2025_UNDERGRAD_PARALLEL_PAGE,
    SHANDONG_2025_REGULAR_BATCH_1_PAGE.source_page_id: SHANDONG_2025_REGULAR_BATCH_1_PAGE,
}


def get_source_page(source_page_id: str) -> SourcePage | None:
    """Look up a registered pilot source page."""

    return SOURCE_PAGES.get(source_page_id)


def build_snapshot(
    *,
    source_page: SourcePage,
    attachment: SourceAttachment,
    raw_file_sha256: str,
    captured_at: datetime,
    operator: str,
    snapshot_id: str | None = None,
) -> SourceSnapshot:
    """Build validated snapshot metadata after a raw file has been captured."""

    return SourceSnapshot(
        source_batch_id=f"{source_page.province}-{source_page.year}-{attachment.raw_format}",
        source_page_id=source_page.source_page_id,
        snapshot_id=snapshot_id or f"{source_page.source_page_id}-{captured_at.date().isoformat()}",
        captured_at=captured_at,
        raw_file_name=attachment.file_name,
        raw_file_url=attachment.url,
        raw_file_sha256=raw_file_sha256,
        operator=operator,
    )


def build_manual_snapshot(
    *,
    source_page: SourcePage,
    raw_file_name: str,
    raw_file_url: str,
    raw_file_sha256: str,
    captured_at: datetime,
    operator: str,
    snapshot_id: str | None = None,
) -> SourceSnapshot:
    """Build snapshot metadata for reviewed manual or browser-captured source data."""

    return SourceSnapshot(
        source_batch_id=f"{source_page.province}-{source_page.year}-manual",
        source_page_id=source_page.source_page_id,
        snapshot_id=snapshot_id or f"{source_page.source_page_id}-{captured_at.date().isoformat()}",
        captured_at=captured_at,
        raw_file_name=raw_file_name,
        raw_file_url=raw_file_url,
        raw_file_sha256=raw_file_sha256,
        operator=operator,
    )
