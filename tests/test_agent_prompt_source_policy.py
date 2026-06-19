"""Agent prompt source policy contract tests."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = PROJECT_ROOT / "SKILL.md"


class AgentPromptSourcePolicyTest(unittest.TestCase):
    def test_skill_prompt_includes_answer_source_policy_contract(self):
        prompt = SKILL_PATH.read_text(encoding="utf-8")

        required_terms = [
            "工具来源策略（必须遵守）",
            "answer_source_policy",
            "answer_mode=citeable",
            "answer_mode=citeable_with_caution",
            "answer_mode=unsupported",
            "legacy_untraced_tool",
            "不能当作真实数据证据",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, prompt)


if __name__ == "__main__":
    unittest.main()
