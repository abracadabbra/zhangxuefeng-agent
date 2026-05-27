"""指标收集器 — 追踪响应时间、调用成功率、LLM 用量"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LLMUsage:
    """LLM 调用统计"""
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: int = 0
    last_reset: datetime = field(default_factory=datetime.now)


@dataclass
class RequestMetrics:
    """请求指标"""
    total_requests: int = 0
    total_errors: int = 0
    total_duration_ms: float = 0.0
    slow_requests: int = 0  # > 5s
    last_reset: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """全局指标收集器"""

    def __init__(self):
        self.llm_usage = LLMUsage()
        self.request_metrics = RequestMetrics()
        self._cost_alert_threshold_usd: float = 50.0
        self._slow_threshold_ms: float = 5000.0

    def record_llm_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> None:
        """记录一次 LLM 调用"""
        self.llm_usage.total_calls += 1
        self.llm_usage.total_prompt_tokens += prompt_tokens
        self.llm_usage.total_completion_tokens += completion_tokens

        # 估算成本（GPT-4o-mini: $0.15/1M input, $0.60/1M output）
        cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
        self.llm_usage.total_cost_usd += cost

        if self.llm_usage.total_cost_usd >= self._cost_alert_threshold_usd:
            logger.warning(
                "成本预警：OpenAI 累计费用 $%.2f 超过阈值 $%.2f",
                self.llm_usage.total_cost_usd,
                self._cost_alert_threshold_usd,
            )

    def record_llm_error(self) -> None:
        """记录 LLM 调用失败"""
        self.llm_usage.errors += 1

    def record_request(self, duration_ms: float, status_code: int) -> None:
        """记录一次 HTTP 请求"""
        self.request_metrics.total_requests += 1
        self.request_metrics.total_duration_ms += duration_ms

        if status_code >= 500:
            self.request_metrics.total_errors += 1

        if duration_ms > self._slow_threshold_ms:
            self.request_metrics.slow_requests += 1
            logger.warning("慢请求：%.1fms (阈值 %.1fms)", duration_ms, self._slow_threshold_ms)

    def get_summary(self) -> dict:
        """获取指标摘要"""
        avg_duration = (
            self.request_metrics.total_duration_ms / self.request_metrics.total_requests
            if self.request_metrics.total_requests > 0
            else 0
        )
        success_rate = (
            1 - self.request_metrics.total_errors / self.request_metrics.total_requests
            if self.request_metrics.total_requests > 0
            else 1.0
        )

        return {
            "requests": {
                "total": self.request_metrics.total_requests,
                "errors": self.request_metrics.total_errors,
                "avg_duration_ms": round(avg_duration, 1),
                "slow_requests": self.request_metrics.slow_requests,
                "success_rate": round(success_rate, 4),
            },
            "llm": {
                "total_calls": self.llm_usage.total_calls,
                "errors": self.llm_usage.errors,
                "prompt_tokens": self.llm_usage.total_prompt_tokens,
                "completion_tokens": self.llm_usage.total_completion_tokens,
                "total_cost_usd": round(self.llm_usage.total_cost_usd, 4),
            },
        }

    def set_cost_alert_threshold(self, threshold_usd: float) -> None:
        """设置成本预警阈值"""
        self._cost_alert_threshold_usd = threshold_usd


# 全局单例
metrics = MetricsCollector()
