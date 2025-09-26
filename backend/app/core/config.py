"""Application configuration via pydantic settings."""

from functools import lru_cache
from pathlib import Path

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    app_env: str = Field("local", alias="APP_ENV")
    app_name: str = "Eastern Iowa Pet Resort API"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(..., alias="DATABASE_URL")
    sync_database_url: str | None = Field(default=None, alias="SYNC_DATABASE_URL")

    secret_key: str = Field(..., alias="SECRET_KEY")
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int | None = Field(default=None, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(default=None, alias="SMTP_FROM")

    stripe_publishable_key: str | None = Field(
        default=None, alias="STRIPE_PUBLISHABLE_KEY"
    )
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(
        default=None, alias="STRIPE_WEBHOOK_SECRET"
    )
    stripe_terminal_location: str | None = Field(
        default=None, alias="STRIPE_TERMINAL_LOCATION"
    )

    payments_webhook_verify: bool = Field(default=True, alias="PAYMENTS_WEBHOOK_VERIFY")
    portal_account_slug: str | None = Field(default=None, alias="PORTAL_ACCOUNT_SLUG")

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_messaging_service_sid: str | None = Field(
        default=None, alias="TWILIO_MESSAGING_SERVICE_SID"
    )

    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")

    qbo_export_dir: str | None = Field(default=None, alias="QBO_EXPORT_DIR")

    kisi_api_key: str | None = Field(default=None, alias="KISI_API_KEY")
    kisi_door_id: str | None = Field(default=None, alias="KISI_DOOR_ID")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        case_sensitive=False,
    )

    def model_post_init(self, __context: Any) -> None:
        """Populate JWT secret from the generic secret when not provided."""

        if not self.jwt_secret_key:
            object.__setattr__(self, "jwt_secret_key", self.secret_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[call-arg]
