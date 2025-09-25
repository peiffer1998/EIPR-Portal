"""Application configuration via pydantic settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    app_env: str = "development"
    app_name: str = "Eastern Iowa Pet Resort API"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    redis_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[arg-type]
