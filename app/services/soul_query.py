"""
灵魂追问引擎 — 张雪峰风格

核心逻辑：
1. 检查必问字段缺失情况
2. 生成张雪峰风格的追问话术（多轮不同、语境感知）
3. 最多 3 轮追问，避免烦人
4. 支持组合追问（一次问多个相关字段）
"""
from dataclasses import dataclass, field
from app.models.user_profile import UserProfile

# 最大追问轮次
MAX_QUERY_ROUNDS = 3

# 必问字段的张雪峰风格话术（每个字段多轮不同话术，更自然）
REQUIRED_QUESTIONS: dict[str, list[str]] = {
    "score": [
        "你孩子考了多少分？先把这个告诉我。分数是一切的基础。",
        "分数出来了吗？多少分？我得先知道这个才能给你分析。",
        "孩子成绩怎么样？多少分？别磨叽，直接说数字。",
        "考了多少分？这是第一步，我得拿这个来判断。",
    ],
    "province": [
        "哪个省的？这个太重要了，不同省差别太大了，河南和北京完全是两个世界。",
        "你是哪个省的考生？我得知道你在哪个省，才能给你分析能上什么学校。",
        "孩子在哪儿参加高考的？省份不一样，能选的学校完全不一样。",
        "哪个省？560分在河南和在北京，那是两个概念。",
    ],
    "subject": [
        "文科还是理科？新高考的话选的哪几科？这个直接影响专业选择。",
        "孩子是文科生还是理科生？新高考省份告诉我选科组合。",
        "文理分科说一下，理工科和文科的策略完全不同。",
        "选的什么科？物理+化学？还是历史+政治？这个很关键。",
    ],
    "family_background": [
        "家里什么条件？做生意的还是工薪阶层？这个决定了完全不同的策略。",
        "家里经济情况怎么样？我得知道这个，有矿和没矿的打法完全不一样。",
        "家庭条件说一下，这关系到选学校选专业的大方向。普通家庭和有钱人家的策略天差地别。",
        "父母做什么的？家里条件怎么样？别嫌我问得多，这个真的很重要。",
    ],
}

# 选问字段话术（更自然的引导）
OPTIONAL_QUESTIONS: dict[str, list[str]] = {
    "target_city": [
        "有没有特别想去的城市？北上广深还是其他地方？城市选择也很关键。",
        "孩子想去哪儿上学？这个也挺关键的，不同城市机会完全不一样。",
        "有没有心仪的城市？北京上海还是无所谓？",
    ],
    "risk_tolerance": [
        "你们是想稳一点还是可以冲一冲？保守选还是激进选？",
        "填报志愿的时候，是求稳还是愿意冒险冲好学校？",
        "你们家的策略是稳妥为主还是可以搏一搏？",
    ],
    "career_goal": [
        "孩子以后想干什么？有没有明确的职业方向？",
        "有没有想好以后从事什么行业？这个影响专业选择。",
        "孩子对什么感兴趣？以后想做什么工作？",
    ],
}

# 组合追问模板（一次问多个相关字段，更高效）
COMBINED_QUESTIONS: list[dict] = [
    {
        "fields": ["score", "province"],
        "question": "你孩子考了多少分？哪个省的？这两个是最基础的，我得先知道。",
    },
    {
        "fields": ["score", "province", "subject"],
        "question": "分数、省份、文理科，这三个一起告诉我，我好给你分析。",
    },
    {
        "fields": ["family_background", "target_city"],
        "question": "家里什么条件？有没有想去的城市？这两个一起说，我好综合考虑。",
    },
]

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

    优化：
    - 支持组合追问（一次问多个字段）
    - 话术去重（同一字段不同轮次用不同话术）
    - 语境感知（根据已有信息调整追问方式）
    """

    def get_next_question(self, profile: UserProfile, state: QueryState) -> str | None:
        """
        获取下一个追问问题

        逻辑：
        1. 如果追问轮次 >= 3，停止追问
        2. 优先尝试组合追问（一次获取多个字段）
        3. 单字段追问必问字段
        4. 必问字段问完后，可选问选问字段（但不强制）
        5. 返回 None 表示不需要再追问
        """
        if state.round_count >= MAX_QUERY_ROUNDS:
            return None

        # 优先尝试组合追问
        combined = self._try_combined_question(profile, state)
        if combined:
            return combined

        # 单字段追问必问字段
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
            if value is None and field_name not in state.asked_fields and field_name not in state.skipped_fields:
                question = self._pick_optional_question(field_name)
                state.asked_fields.append(field_name)
                state.round_count += 1
                return question

        return None

    def _try_combined_question(self, profile: UserProfile, state: QueryState) -> str | None:
        """尝试组合追问，一次获取多个缺失字段"""
        missing = set(profile.missing_required_fields()) - set(state.asked_fields)

        for combo in COMBINED_QUESTIONS:
            combo_fields = set(combo["fields"])
            # 如果组合中的所有字段都缺失，且至少有2个未问过
            if combo_fields.issubset(missing) and len(combo_fields - set(state.asked_fields)) >= 2:
                for f in combo_fields:
                    state.asked_fields.append(f)
                state.round_count += 1
                return combo["question"]

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
        idx = round_count % len(questions)
        return questions[idx]

    def _pick_optional_question(self, field_name: str) -> str:
        """选问字段的话术"""
        questions = OPTIONAL_QUESTIONS.get(field_name, [])
        if not questions:
            return f"方便的话告诉我你的{field_name}"
        return questions[0]
