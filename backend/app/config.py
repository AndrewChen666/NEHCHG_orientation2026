from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "活米村遊戲伺服器"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str | None = None
    session_secret: str = "development-only-change-me"
    cors_origins: str = "http://localhost:5173"
    session_ttl_minutes: int = 720

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

