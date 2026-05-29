"""上下文裁剪测试"""
import pytest
from backend.agent.core import _trim_messages, MAX_HISTORY_ROUNDS


def _make_messages(n_rounds: int) -> list[dict]:
    """构造 n 轮对话消息（system + n * 2 条）"""
    messages = [{"role": "system", "content": "你是一个 AI 助手"}]
    for i in range(n_rounds):
        messages.append({"role": "user", "content": f"用户消息 {i}"})
        messages.append({"role": "assistant", "content": f"助手回复 {i}"})
    return messages


class TestTrimMessages:
    def test_short_history_not_trimmed(self):
        """消息数未超阈值时不裁剪"""
        messages = _make_messages(5)
        result = _trim_messages(messages)
        assert len(result) == len(messages)

    def test_exact_threshold_not_trimmed(self):
        """恰好等于阈值时不裁剪"""
        messages = _make_messages(MAX_HISTORY_ROUNDS)
        result = _trim_messages(messages)
        assert len(result) == len(messages)

    def test_long_history_trimmed(self):
        """超过阈值时裁剪到保留最近 N 轮"""
        messages = _make_messages(50)
        result = _trim_messages(messages)
        assert len(result) == 1 + MAX_HISTORY_ROUNDS * 2

    def test_system_prompt_always_preserved(self):
        """system prompt 始终保留"""
        messages = _make_messages(50)
        result = _trim_messages(messages)
        assert result[0]["role"] == "system"

    def test_recent_messages_preserved(self):
        """最近的消息被保留"""
        messages = _make_messages(50)
        result = _trim_messages(messages)
        # 最后一条应该是最后一轮的 assistant 回复
        assert result[-1]["content"] == "助手回复 49"
        assert result[-2]["content"] == "用户消息 49"

    def test_old_messages_dropped(self):
        """最旧的消息被丢弃"""
        messages = _make_messages(50)
        result = _trim_messages(messages)
        # 第 0 轮的消息应该被丢弃
        contents = [m["content"] for m in result]
        assert "用户消息 0" not in contents
        assert "助手回复 0" not in contents

    def test_custom_max_rounds(self):
        """自定义 max_rounds 参数"""
        messages = _make_messages(20)
        result = _trim_messages(messages, max_rounds=5)
        assert len(result) == 1 + 5 * 2

    def test_single_system_message(self):
        """只有一条 system 消息时不报错"""
        messages = [{"role": "system", "content": "test"}]
        result = _trim_messages(messages)
        assert len(result) == 1
