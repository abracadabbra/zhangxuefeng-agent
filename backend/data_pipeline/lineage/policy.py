"""Answer-level source policy helpers for Agent/tool responses."""

from collections.abc import Mapping


def build_answer_source_policy(source_summary: Mapping[str, object] | None) -> dict:
    """Project source summary into Agent answer guidance."""
    if not source_summary:
        return {
            "answer_mode": "unsupported",
            "citation_ready": False,
            "requires_citation": False,
            "requires_caution": True,
            "allowed_default_answer": False,
            "reasons": ["missing_source_summary"],
        }

    metadata_complete = source_summary.get("source_metadata_complete") is not False
    citation_ready = source_summary.get("citation_ready") is True
    citation_ready = citation_ready and metadata_complete
    needs_caution = (
        source_summary.get("needs_caution") is True
        or not metadata_complete
    )
    reasons = _answer_policy_reasons(source_summary, citation_ready, needs_caution)

    if citation_ready and not needs_caution:
        answer_mode = "citeable"
    elif citation_ready:
        answer_mode = "citeable_with_caution"
    else:
        answer_mode = "unsupported"

    return {
        "answer_mode": answer_mode,
        "citation_ready": citation_ready,
        "requires_citation": citation_ready,
        "requires_caution": answer_mode != "citeable",
        "allowed_default_answer": answer_mode == "citeable",
        "reasons": reasons,
    }


def _answer_policy_reasons(
    source_summary: Mapping[str, object],
    citation_ready: bool,
    needs_caution: bool,
) -> list[str]:
    reasons = []
    item_count = _int_or_none(source_summary.get("item_count"))
    items_with_sources = _int_or_none(source_summary.get("items_with_sources"))
    source_count = _int_or_none(source_summary.get("source_count"))
    source_status = source_summary.get("source_status")
    metadata_complete = source_summary.get("source_metadata_complete")

    if source_status == "legacy_untraced":
        reasons.append("legacy_untraced_tool")
    if metadata_complete is False:
        reasons.append("source_metadata_incomplete")
    if item_count == 0:
        reasons.append("no_result_items")
    if source_count == 0:
        reasons.append("no_sources")
    if (
        item_count is not None
        and items_with_sources is not None
        and items_with_sources < item_count
    ):
        reasons.append("partial_source_coverage")
    elif not citation_ready:
        reasons.append("not_citation_ready")
    if needs_caution:
        reasons.append("source_caution_required")
    return reasons


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
