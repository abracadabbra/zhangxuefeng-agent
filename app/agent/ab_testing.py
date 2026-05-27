"""
A/B 测试框架 — Prompt 版本管理与效果追踪

支持：
- 多版本 Prompt 管理
- 流量分配（百分比）
- 效果指标追踪（满意度、响应时间、token 用量）
"""

import random
import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.core.metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class PromptVariant:
    """Prompt 变体"""
    name: str
    description: str
    weight: int = 1  # 权重，用于流量分配
    prompt_builder: str = "default"  # 构建函数名称
    created_at: datetime = field(default_factory=datetime.now)
    # 效果统计
    total_calls: int = 0
    total_satisfaction: float = 0.0  # 累计满意度评分
    total_response_time_ms: float = 0.0
    total_tokens: int = 0


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self):
        self._variants: dict[str, PromptVariant] = {}
        self._active_test: str | None = None

    def register_variant(self, variant: PromptVariant) -> None:
        """注册一个 Prompt 变体"""
        self._variants[variant.name] = variant
        logger.info("注册 Prompt 变体: %s (权重=%d)", variant.name, variant.weight)

    def start_test(self, test_name: str, variant_names: list[str]) -> None:
        """启动 A/B 测试"""
        for name in variant_names:
            if name not in self._variants:
                raise ValueError(f"变体 {name} 未注册")

        self._active_test = test_name
        logger.info(
            "启动 A/B 测试: %s | 变体: %s",
            test_name,
            ", ".join(variant_names),
        )

    def select_variant(self) -> PromptVariant | None:
        """根据权重随机选择一个变体"""
        if not self._active_test or not self._variants:
            return None

        variants = list(self._variants.values())
        total_weight = sum(v.weight for v in variants)
        if total_weight == 0:
            return variants[0]

        rand = random.uniform(0, total_weight)
        cumulative = 0.0
        for variant in variants:
            cumulative += variant.weight
            if rand <= cumulative:
                return variant

        return variants[-1]

    def record_result(
        self,
        variant_name: str,
        response_time_ms: float,
        tokens_used: int,
        satisfaction: float | None = None,
    ) -> None:
        """记录一次测试结果"""
        variant = self._variants.get(variant_name)
        if not variant:
            return

        variant.total_calls += 1
        variant.total_response_time_ms += response_time_ms
        variant.total_tokens += tokens_used

        if satisfaction is not None:
            variant.total_satisfaction += satisfaction

    def get_results(self) -> dict:
        """获取测试结果摘要"""
        results = {}
        for name, variant in self._variants.items():
            avg_time = (
                variant.total_response_time_ms / variant.total_calls
                if variant.total_calls > 0
                else 0
            )
            avg_satisfaction = (
                variant.total_satisfaction / variant.total_calls
                if variant.total_calls > 0 and variant.total_satisfaction > 0
                else None
            )
            avg_tokens = (
                variant.total_tokens / variant.total_calls
                if variant.total_calls > 0
                else 0
            )

            results[name] = {
                "description": variant.description,
                "weight": variant.weight,
                "total_calls": variant.total_calls,
                "avg_response_time_ms": round(avg_time, 1),
                "avg_satisfaction": round(avg_satisfaction, 2) if avg_satisfaction else None,
                "avg_tokens": round(avg_tokens, 0),
            }

        return {
            "test_name": self._active_test,
            "variants": results,
        }

    def stop_test(self) -> dict:
        """停止测试并返回最终结果"""
        results = self.get_results()
        self._active_test = None
        logger.info("A/B 测试已停止")
        return results


# 全局单例
ab_test = ABTestManager()


def setup_default_variants() -> None:
    """注册默认的 Prompt 变体"""

    ab_test.register_variant(PromptVariant(
        name="full_prompt",
        description="完整版 Prompt（包含所有模块）",
        weight=50,
        prompt_builder="build_system_prompt",
    ))

    ab_test.register_variant(PromptVariant(
        name="minimal_prompt",
        description="精简版 Prompt（仅核心指令）",
        weight=50,
        prompt_builder="build_minimal_prompt",
    ))
