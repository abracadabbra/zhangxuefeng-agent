"""Agent answer source policy review tests."""

import importlib.util
import json
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_POLICY_PATH = PROJECT_ROOT / "backend" / "agent" / "source_policy.py"

spec = importlib.util.spec_from_file_location("agent_source_policy", SOURCE_POLICY_PATH)
source_policy = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(source_policy)
build_tool_answer_source_policy_review = (
    source_policy.build_tool_answer_source_policy_review
)


def make_tool_call(name: str, policy: dict | None) -> dict:
    payload = {"status": "success"}
    if policy is not None:
        payload["answer_source_policy"] = policy
    return {"name": name, "result": json.dumps(payload, ensure_ascii=False)}


class AgentAnswerSourcePolicyReviewTest(unittest.TestCase):
    def test_review_marks_no_tool_calls_not_applicable(self):
        review = build_tool_answer_source_policy_review([])

        self.assertEqual(review["overall_answer_mode"], "not_applicable")
        self.assertFalse(review["requires_caution"])
        self.assertEqual(review["tool_result_count"], 0)

    def test_review_preserves_citeable_mode(self):
        review = build_tool_answer_source_policy_review(
            [
                make_tool_call(
                    "search_admission",
                    {
                        "answer_mode": "citeable",
                        "requires_citation": True,
                        "requires_caution": False,
                        "reasons": [],
                    },
                )
            ]
        )

        self.assertEqual(review["overall_answer_mode"], "citeable")
        self.assertTrue(review["requires_citation"])
        self.assertFalse(review["requires_caution"])
        self.assertEqual(review["citeable_tools"], ["search_admission"])

    def test_review_upgrades_to_caution_when_any_tool_requires_caution(self):
        review = build_tool_answer_source_policy_review(
            [
                make_tool_call(
                    "search_admission",
                    {
                        "answer_mode": "citeable",
                        "requires_citation": True,
                        "requires_caution": False,
                        "reasons": [],
                    },
                ),
                make_tool_call(
                    "search_enrollment_plan",
                    {
                        "answer_mode": "citeable_with_caution",
                        "requires_citation": True,
                        "requires_caution": True,
                        "reasons": ["source_caution_required"],
                    },
                ),
            ]
        )

        self.assertEqual(review["overall_answer_mode"], "citeable_with_caution")
        self.assertTrue(review["requires_citation"])
        self.assertTrue(review["requires_caution"])
        self.assertEqual(review["cautious_tools"], ["search_enrollment_plan"])
        self.assertEqual(review["reasons"], ["source_caution_required"])

    def test_review_upgrades_to_unsupported_when_any_tool_is_unsupported(self):
        review = build_tool_answer_source_policy_review(
            [
                make_tool_call(
                    "search_admission",
                    {
                        "answer_mode": "citeable",
                        "requires_citation": True,
                        "requires_caution": False,
                        "reasons": [],
                    },
                ),
                make_tool_call(
                    "search_employment",
                    {
                        "answer_mode": "unsupported",
                        "requires_citation": False,
                        "requires_caution": True,
                        "reasons": ["legacy_untraced_tool"],
                    },
                ),
            ]
        )

        self.assertEqual(review["overall_answer_mode"], "unsupported")
        self.assertTrue(review["requires_caution"])
        self.assertEqual(review["unsupported_tools"], ["search_employment"])
        self.assertEqual(review["reasons"], ["legacy_untraced_tool"])

    def test_review_treats_missing_policy_as_unsupported(self):
        review = build_tool_answer_source_policy_review(
            [make_tool_call("semantic_search", None)]
        )

        self.assertEqual(review["overall_answer_mode"], "unsupported")
        self.assertTrue(review["requires_caution"])
        self.assertEqual(review["missing_policy_tools"], ["semantic_search"])
        self.assertEqual(review["reasons"], ["missing_answer_source_policy"])

    def test_review_treats_partial_missing_policy_as_unsupported(self):
        review = build_tool_answer_source_policy_review(
            [
                make_tool_call(
                    "search_admission",
                    {
                        "answer_mode": "citeable",
                        "requires_citation": True,
                        "requires_caution": False,
                        "reasons": [],
                    },
                ),
                make_tool_call("semantic_search", None),
            ]
        )

        self.assertEqual(review["overall_answer_mode"], "unsupported")
        self.assertTrue(review["requires_caution"])
        self.assertEqual(review["missing_policy_tools"], ["semantic_search"])

    def test_review_treats_unknown_answer_mode_as_unsupported(self):
        review = build_tool_answer_source_policy_review(
            [
                make_tool_call(
                    "custom_tool",
                    {
                        "answer_mode": "experimental",
                        "requires_citation": False,
                        "requires_caution": False,
                        "reasons": ["unknown_answer_mode"],
                    },
                )
            ]
        )

        self.assertEqual(review["overall_answer_mode"], "unsupported")
        self.assertEqual(review["unsupported_tools"], ["custom_tool"])


if __name__ == "__main__":
    unittest.main()
