"""SKILL.md 加载服务"""

from pathlib import Path

from app.core.config import get_settings


def load_skill() -> str:
    """加载 SKILL.md 内容作为 system prompt"""
    settings = get_settings()
    skill_path = Path(settings.SKILL_PATH)

    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL.md 未找到: {skill_path}")

    return skill_path.read_text(encoding="utf-8")
