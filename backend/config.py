"""
集中配置管理 -- pydantic-settings 驱动

所有环境变量在此定义、验证、提供默认值。
支持 .env 文件（项目根目录）。
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，从环境变量 / .env 文件读取并验证。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- OpenAI ----------
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API Base URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", description="默认模型名称")
    model: str = Field(default="", description="兼容旧 MODEL 环境变量")

    # ---------- 数据库 ----------
    database_url: str = Field(
        default="sqlite:///./data/zhangxuefeng.db",
        description="SQLAlchemy 数据库连接串",
    )

    # ---------- Redis ----------
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis 连接串")

    # ---------- 应用 ----------
    debug: bool = Field(default=False, description="调试模式")
    skill_path: str = Field(default="SKILL.md", description="SKILL.md 文件路径")
    use_langchain: bool = Field(default=False, description="是否使用 LangChain Agent")
    port: int = Field(default=8000, description="服务端口")

    # ---------- CORS ----------
    cors_origins: str = Field(default="*", description="CORS 允许来源（逗号分隔）")

    # ---------- Sentry ----------
    sentry_dsn: str = Field(default="", description="Sentry DSN")

    # ---------- 成本预警 ----------
    cost_alert_threshold_usd: float = Field(default=50.0, description="成本预警阈值（USD）")

    # ---------- 日志 ----------
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="console",
        description="日志格式：console（开发）或 json（生产）",
    )

    @property
    def effective_model(self) -> str:
        """兼容旧 MODEL 环境变量：优先 openai_model，其次 model。"""
        return self.openai_model or self.model or "gpt-4o-mini"

    @property
    def cors_origins_list(self) -> list[str]:
        """将逗号分隔的 CORS 字符串解析为列表。"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局配置单例（进程生命周期内只解析一次）。"""
    return Settings()
