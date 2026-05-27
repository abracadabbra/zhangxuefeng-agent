"""配置管理 — 使用 pydantic-settings"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量或 .env 文件加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- 应用 ---
    APP_NAME: str = "张雪峰 AI 咨询 Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- OpenAI ---
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL: str = "gpt-4o-mini"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- 数据库 ---
    DATABASE_URL: str = "sqlite:///./data/zhangxuefeng.db"

    # --- SKILL.md ---
    SKILL_PATH: str = "SKILL.md"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["*"]

    # --- 监控 ---
    SENTRY_DSN: str = ""
    COST_ALERT_THRESHOLD_USD: float = 50.0


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
