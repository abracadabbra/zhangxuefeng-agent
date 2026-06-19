"""Raw snapshot manifest model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


CollectorKind = Literal["manual", "crawler_stub", "crawler", "api", "import"]


class ManifestFile(BaseModel):
    """A file stored inside a raw snapshot directory."""

    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    content_type: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def path_must_be_relative(cls, value: str) -> str:
        if value.startswith("/") or ".." in value.split("/"):
            raise ValueError("manifest file paths must be relative and stay inside snapshot")
        return value

    @field_validator("sha256")
    @classmethod
    def sha256_must_be_hex(cls, value: str) -> str:
        if not all(c in "0123456789abcdef" for c in value.lower()):
            raise ValueError("sha256 must be a lowercase or uppercase hex string")
        return value.lower()


class RawSnapshotManifest(BaseModel):
    """Metadata required for every raw data snapshot."""

    snapshot_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    source_url: HttpUrl
    published_year: int = Field(ge=2000, le=2100)
    collected_at: datetime
    collector: CollectorKind = "manual"
    collector_version: str = Field(min_length=1)
    files: list[ManifestFile] = Field(min_length=1)
    license_note: str = Field(min_length=1)

    @field_validator("snapshot_id", "source_id", "dataset")
    @classmethod
    def identifiers_are_slug_like(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if any(c not in allowed for c in value):
            raise ValueError("identifier must contain only letters, numbers, hyphen, or underscore")
        return value
