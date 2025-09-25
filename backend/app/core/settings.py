"""Specialized settings adapters for integrations."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.config import get_settings


class PaymentSettings(BaseModel):
    """Slim view of payment-related configuration."""

    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: str | None = None
    payments_webhook_verify: bool = True


def get_payment_settings() -> PaymentSettings:
    """Return payment-specific configuration."""

    settings = get_settings()
    return PaymentSettings(
        stripe_secret_key=settings.stripe_secret_key or None,
        stripe_publishable_key=settings.stripe_publishable_key or None,
        stripe_webhook_secret=settings.stripe_webhook_secret or None,
        payments_webhook_verify=settings.payments_webhook_verify,
    )
