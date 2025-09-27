"""Application configuration via pydantic settings."""

from functools import lru_cache
from pathlib import Path

from typing import Any

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    app_env: str = Field("local", alias="APP_ENV")
    app_name: str = "Eastern Iowa Pet Resort API"
    app_encryption_key: str = Field(..., alias="APP_ENCRYPTION_KEY")
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
    portal_confirmation_success_url: str = Field(
        "/portal/confirmation-success", alias="PORTAL_CONFIRMATION_SUCCESS_URL"
    )
    portal_confirmation_expired_url: str = Field(
        "/portal/confirmation-expired", alias="PORTAL_CONFIRMATION_EXPIRED_URL"
    )

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_messaging_service_sid: str | None = Field(
        default=None, alias="TWILIO_MESSAGING_SERVICE_SID"
    )
    dev_sms_echo: bool = Field(default=False, alias="DEV_SMS_ECHO")

    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")

    image_max_width: int = Field(1600, alias="IMAGE_MAX_WIDTH")
    image_webp_quality: int = Field(82, alias="IMAGE_WEBP_QUALITY")
    image_keep_original_days: int = Field(90, alias="IMAGE_KEEP_ORIGINAL_DAYS")
    image_dedup: bool = Field(True, alias="IMAGE_DEDUP")
    s3_cache_seconds: int = Field(31536000, alias="S3_CACHE_SECONDS")

    qbo_export_dir: str | None = Field(default=None, alias="QBO_EXPORT_DIR")

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
        ],
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_origin_regex: str | None = Field(
        default=None, alias="CORS_ALLOW_ORIGIN_REGEX"
    )
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_allowlist: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"], alias="CORS_ALLOWLIST"
    )

    rate_limit_default: str = Field("100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_login: str = Field("10/minute", alias="RATE_LIMIT_LOGIN")
    export_redact: bool = Field(True, alias="EXPORT_REDACT")

    gingr_mysql_host: str | None = Field(default=None, alias="GINGR_MYSQL_HOST")
    gingr_mysql_port: int | None = Field(default=None, alias="GINGR_MYSQL_PORT")
    gingr_mysql_db: str | None = Field(default=None, alias="GINGR_MYSQL_DB")
    gingr_mysql_user: str | None = Field(default=None, alias="GINGR_MYSQL_USER")
    gingr_mysql_password: str | None = Field(default=None, alias="GINGR_MYSQL_PASSWORD")

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

    @field_validator("cors_allow_origins", "cors_allowlist", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[call-arg]
