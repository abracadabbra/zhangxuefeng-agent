"""Shared time helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a naive UTC datetime for existing SQLAlchemy DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)
