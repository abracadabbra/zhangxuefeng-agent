"""
对话上下文管理 — 实体提取 + 窗口管理

功能：
- 从对话中提取实体信息（分数、省份、科类等）
- 管理对话窗口大小，避免超出 token 限制
- 构建包含上下文的消息列表
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedEntities:
    """从对话中提取的实体"""
    score: Optional[int] = None
    province: Optional[str] = None
    subject: Optional[str] = None
    family_background: Optional[str] = None
    target_city: Optional[str] = None
    career_goal: Optional[str] = None


# 省份列表
PROVINCES = [
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
    "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
    "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西",
    "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
]


def extract_entities(message: str) -> ExtractedEntities:
    """从单条消息中提取实体"""
    entities = ExtractedEntities()

    # 提取分数（xx 分 或 纯数字）
    score_match = re.search(r'(\d{2,3})\s*分', message)
    if score_match:
        score = int(score_match.group(1))
        if 100 <= score <= 750:
            entities.score = score

    # 提取省份
    for p in PROVINCES:
        if p in message:
            entities.province = p
            break

    # 提取文理科
    if "文科" in message:
        entities.subject = "文科"
    elif "理科" in message:
        entities.subject = "理科"

    # 提取家庭条件关键词
    family_keywords = {
        "做生意": "经商家庭",
        "经商": "经商家庭",
        "工薪": "工薪阶层",
        "打工": "工薪阶层",
        "公务员": "公务员家庭",
        "农民": "农村家庭",
        "务农": "农村家庭",
    }
    for keyword, value in family_keywords.items():
        if keyword in message:
            entities.family_background = value
            break

    # 提取目标城市
    city_keywords = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉"]
    for city in city_keywords:
        if city in message and "想去" in message or "目标" in message:
            entities.target_city = city
            break

    return entities


def merge_entities(
    existing: ExtractedEntities,
    new: ExtractedEntities,
) -> ExtractedEntities:
    """合并实体，新值覆盖旧的 None 值"""
    return ExtractedEntities(
        score=new.score if new.score is not None else existing.score,
        province=new.province if new.province is not None else existing.province,
        subject=new.subject if new.subject is not None else existing.subject,
        family_background=new.family_background if new.family_background is not None else existing.family_background,
        target_city=new.target_city if new.target_city is not None else existing.target_city,
        career_goal=new.career_goal if new.career_goal is not None else existing.career_goal,
    )


def build_context_messages(
    skill_content: str,
    history: list[dict],
    user_message: str,
    user_context: dict,
    window_size: int = 20,
) -> list[dict]:
    """
    构建发送给 LLM 的消息列表

    Args:
        skill_content: SKILL.md 内容
        history: 历史消息列表
        user_message: 当前用户消息
        user_context: 用户上下文信息
        window_size: 历史消息窗口大小
    """
    system_content = skill_content

    # 注入用户上下文
    if user_context:
        ctx_parts = []
        mapping = {
            "分数": "考生分数：{0}分",
            "省份": "所在省份：{0}",
            "科类": "文理科：{0}",
            "家庭条件": "家庭条件：{0}",
            "目标城市": "目标城市：{0}",
            "风险偏好": "风险偏好：{0}",
            "职业方向": "职业方向：{0}",
        }
        for key, template in mapping.items():
            value = user_context.get(key)
            if value:
                ctx_parts.append(f"- {template.format(value)}")

        if ctx_parts:
            system_content += "\n\n## 用户背景信息\n" + "\n".join(ctx_parts)

    messages = [{"role": "system", "content": system_content}]

    # 添加历史消息（窗口限制）
    windowed_history = history[-window_size:] if len(history) > window_size else history
    for msg in windowed_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # 添加当前消息
    messages.append({"role": "user", "content": user_message})

    return messages
