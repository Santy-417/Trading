from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    supabase_service_role_key: str = ""
    database_url: str

    # MetaTrader 5
    mt5_login: int
    mt5_password: str
    mt5_server: str = "MetaQuotes-Demo"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = ""

    # Risk Management
    max_daily_loss_percent: float = 3.0
    max_drawdown_percent: float = 10.0
    max_trades_per_hour: int = 10
    default_risk_per_trade: float = 1.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
