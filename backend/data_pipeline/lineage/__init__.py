"""Lineage persistence helpers for real-data pipeline records."""

from typing import Any

__all__ = [
    "SourceMetadataConfig",
    "build_answer_source_policy",
    "create_lineage_record",
    "get_lineage_for_entity",
    "get_lineage_for_snapshot",
    "get_snapshot",
    "get_sources_for_entity",
    "get_source",
    "upsert_snapshot",
    "upsert_source",
    "summarize_sources",
]


def __getattr__(name: str) -> Any:
    if name == "build_answer_source_policy":
        from backend.data_pipeline.lineage.policy import build_answer_source_policy

        return build_answer_source_policy
    if name in {
        "create_lineage_record",
        "get_lineage_for_entity",
        "get_lineage_for_snapshot",
        "get_snapshot",
        "get_source",
        "upsert_snapshot",
        "upsert_source",
    }:
        from backend.data_pipeline.lineage import service

        return getattr(service, name)
    if name in {
        "SourceMetadataConfig",
        "get_sources_for_entity",
        "summarize_sources",
    }:
        from backend.data_pipeline.lineage import sources

        return getattr(sources, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
