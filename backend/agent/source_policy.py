"""Helpers for summarizing tool answer source policy."""

import json
from typing import Any


ANSWER_MODE_ORDER = {
    "not_applicable": 0,
    "citeable": 1,
    "citeable_with_caution": 2,
    "unsupported": 3,
}


def build_tool_answer_source_policy_review(tool_calls: list[dict]) -> dict:
    """Build a conservative answer source policy review for tool results."""
    policies = []
    missing_policy_tools = []

    for tool_call in tool_calls:
        tool_name = str(tool_call.get("name") or "")
        policy = _extract_answer_source_policy(tool_call.get("result"))
        if policy is None:
            missing_policy_tools.append(tool_name)
            continue
        answer_mode = str(policy.get("answer_mode") or "unsupported")
        if answer_mode not in ANSWER_MODE_ORDER:
            answer_mode = "unsupported"
        policies.append(
            {
                "tool": tool_name,
                "answer_mode": answer_mode,
                "requires_citation": policy.get("requires_citation") is True,
                "requires_caution": policy.get("requires_caution") is True,
                "reasons": _string_list(policy.get("reasons")),
            }
        )

    overall_mode = _overall_answer_mode(
        policies,
        bool(tool_calls),
        bool(missing_policy_tools),
    )
    return {
        "tool_result_count": len(tool_calls),
        "policy_count": len(policies),
        "overall_answer_mode": overall_mode,
        "requires_citation": any(p["requires_citation"] for p in policies),
        "requires_caution": _requires_caution(overall_mode, policies, tool_calls),
        "citeable_tools": _tools_by_mode(policies, "citeable"),
        "cautious_tools": _tools_by_mode(policies, "citeable_with_caution"),
        "unsupported_tools": _tools_by_mode(policies, "unsupported"),
        "missing_policy_tools": missing_policy_tools,
        "reasons": _unique_reasons(policies, missing_policy_tools),
    }


def _extract_answer_source_policy(result: object) -> dict | None:
    payload = result
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    policy = payload.get("answer_source_policy")
    if isinstance(policy, dict):
        return policy
    return None


def _overall_answer_mode(
    policies: list[dict],
    has_tool_calls: bool,
    has_missing_policy: bool,
) -> str:
    if not has_tool_calls:
        return "not_applicable"
    if has_missing_policy or not policies:
        return "unsupported"
    return max(
        (str(policy.get("answer_mode") or "unsupported") for policy in policies),
        key=lambda mode: ANSWER_MODE_ORDER.get(mode, ANSWER_MODE_ORDER["unsupported"]),
    )


def _requires_caution(
    overall_mode: str,
    policies: list[dict],
    tool_calls: list[dict],
) -> bool:
    if overall_mode in {"unsupported", "citeable_with_caution"}:
        return True
    if bool(tool_calls) and not policies:
        return True
    return any(policy["requires_caution"] for policy in policies)


def _tools_by_mode(policies: list[dict], mode: str) -> list[str]:
    return [
        str(policy["tool"])
        for policy in policies
        if policy.get("answer_mode") == mode and policy.get("tool")
    ]


def _unique_reasons(policies: list[dict], missing_policy_tools: list[str]) -> list[str]:
    reasons: list[str] = []
    if missing_policy_tools:
        reasons.append("missing_answer_source_policy")
    for policy in policies:
        for reason in policy["reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    return reasons


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
