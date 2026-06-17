"""
灵魂追问引擎 — 张雪峰风格

核心逻辑：
1. 检查必问字段缺失情况
2. 生成张雪峰风格的追问话术
3. 最多 3 轮追问，避免烦人
"""

from dataclasses import dataclass, field

from backend.user_profile import UserProfile

# 最大追问轮次
MAX_QUERY_ROUNDS = 5

# 必问字段的张雪峰风格话术
REQUIRED_QUESTIONS: dict[str, list[str]] = {
    "score": [
        "你孩子考了多少分？先把这个告诉我。",
        "分数多少？这是最基础的，我得先知道这个才能给你建议。",
        "孩子高考成绩出来了吗？多少分？别磨叽，直接说。",
    ],
    "province": [
        "哪个省的？这个很重要，不同省差别太大了。",
        "你是哪个省的考生？我得知道你在哪个省，才能给你分析。",
        "孩子在哪儿参加的高考？省份不一样，策略完全不一样。",
    ],
    "subject": [
        "文科还是理科？新高考的话选的哪几科？",
        "孩子是文科生还是理科生？新高考省份告诉我选科组合。",
        "文理分科情况说一下，这个直接影响专业选择。",
    ],
    "family_background": [
        "家里什么条件？做生意的还是工薪阶层？这个决定了完全不同的策略。",
        "家里经济情况怎么样？是普通工薪家庭还是做生意的？",
        "家庭条件说一下，这关系到选学校选专业的大方向。",
    ],
}

# 选问字段话术（可选，不强制追问）
OPTIONAL_QUESTIONS: dict[str, list[str]] = {
    "target_city": [
        "有没有特别想去的城市？北上广深还是其他地方？",
        "孩子想去哪个城市发展？这个也挺关键的。",
    ],
    "risk_tolerance": [
        "你家是想稳一点还是可以冲一冲？保守选还是激进选？",
        "填报志愿的时候，你们是求稳还是愿意冲一冲好学校？",
    ],
    "career_goal": [
        "孩子以后想干什么？有没有明确的职业方向？",
        "有没有想好以后从事什么行业？这个影响专业选择。",
    ],
}

# 字段跳过时的默认值策略
SKIP_DEFAULTS: dict[str, str] = {
    "target_city": "不限",
    "risk_tolerance": "稳健",
    "career_goal": "未确定",
}


@dataclass
class QueryState:
    """追问状态跟踪"""

    round_count: int = 0
    asked_fields: list[str] = field(default_factory=list)
    skipped_fields: list[str] = field(default_factory=list)


class SoulQueryEngine:
    """
    灵魂追问引擎

    接口：
    - get_next_question(profile, state) -> str | None
    - handle_skip(state, field) -> None
    - is_query_complete(profile) -> bool
    """

    def get_next_question(self, profile: UserProfile, state: QueryState) -> str | None:
        """
        获取下一个追问问题

        逻辑：
        1. 如果追问轮次 >= 3，停止追问
        2. 先检查必问字段
        3. 必问字段问完后，可选问选问字段（但不强制）
        4. 返回 None 表示不需要再追问
        """
        if state.round_count >= MAX_QUERY_ROUNDS:
            return None

        # 优先追问必问字段
        missing_required = profile.missing_required_fields()
        for field_name in missing_required:
            if field_name not in state.asked_fields:
                question = self._pick_question(field_name, state.round_count)
                state.asked_fields.append(field_name)
                state.round_count += 1
                return question

        # 必问字段已全，追问选问字段（最多再问 1 个）
        optional_fields = ["target_city", "risk_tolerance", "career_goal"]
        for field_name in optional_fields:
            value = getattr(profile, field_name, None)
            if (
                value is None
                and field_name not in state.asked_fields
                and field_name not in state.skipped_fields
            ):
                question = self._pick_optional_question(field_name)
                state.asked_fields.append(field_name)
                state.round_count += 1
                return question

        return None

    def handle_skip(self, state: QueryState, field_name: str) -> None:
        """用户跳过某问题时，记录并应用默认值"""
        if field_name not in state.skipped_fields:
            state.skipped_fields.append(field_name)

    def is_query_complete(self, profile: UserProfile) -> bool:
        """判断是否还需要追问（必问字段全部填写即完成）"""
        return profile.is_required_complete()

    def get_skip_default(self, field_name: str) -> str | None:
        """获取字段跳过时的默认值"""
        return SKIP_DEFAULTS.get(field_name)

    def _pick_question(self, field_name: str, round_count: int) -> str:
        """根据轮次选择话术，避免重复"""
        questions = REQUIRED_QUESTIONS.get(field_name, [])
        if not questions:
            return f"请告诉我你的{field_name}"
        # 按轮次取话术，循环使用
        idx = round_count % len(questions)
        return questions[idx]

    def _pick_optional_question(self, field_name: str) -> str:
        """选问字段的话术"""
        questions = OPTIONAL_QUESTIONS.get(field_name, [])
        if not questions:
            return f"方便的话告诉我你的{field_name}"
        return questions[0]
