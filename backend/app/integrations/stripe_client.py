"""Minimal Stripe client wrapper with idempotency helpers."""

from __future__ import annotations

import importlib
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast


@dataclass(slots=True)
class PaymentIntent:
    """Simplified payment intent payload."""

    id: str
    client_secret: str | None
    status: str
    metadata: dict[str, Any]


class StripeClientError(RuntimeError):
    """Raised when Stripe interaction fails."""


class StripeClient:
    """Wrapper around the Stripe SDK with optional test mode."""

    def __init__(
        self,
        secret_key: str,
        *,
        webhook_secret: str | None = None,
        test_mode: bool = False,
        idempotency_prefix: str = "eipr",
    ) -> None:
        self._secret_key = secret_key
        self._webhook_secret = webhook_secret
        self._test_mode = test_mode
        self._idempotency_prefix = idempotency_prefix
        self._stripe: Any | None = None
        try:
            stripe_module = importlib.import_module("stripe")
        except ModuleNotFoundError:  # pragma: no cover - dependency missing in tests
            self._stripe = None
        else:
            stripe_obj = cast(Any, stripe_module)
            stripe_obj.api_key = secret_key
            stripe_obj.max_network_retries = 2
            self._stripe = stripe_obj

    @property
    def webhook_secret(self) -> str | None:
        return self._webhook_secret

    def _idempotency_key(self, seed: str | uuid.UUID) -> str:
        return f"{self._idempotency_prefix}_{seed}"

    def create_payment_intent(
        self,
        *,
        amount: Decimal,
        invoice_id: uuid.UUID,
        currency: str = "usd",
        metadata: dict[str, Any] | None = None,
    ) -> PaymentIntent:
        metadata = metadata or {}
        metadata.setdefault("invoice_id", str(invoice_id))
        cents = int((amount * 100).quantize(Decimal("1")))
        kwargs: dict[str, Any] = {
            "amount": cents,
            "currency": currency,
            "metadata": metadata,
            "confirmation_method": "manual",
            "confirm": False,
        }
        if self._test_mode:
            kwargs.setdefault("payment_method_types", ["card"])
        if self._stripe is None:
            raise StripeClientError("Stripe SDK is not installed")
        try:
            intent = self._stripe.PaymentIntent.create(
                **kwargs,
                idempotency_key=self._idempotency_key(invoice_id),
            )
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Failed to create payment intent") from exc
        return PaymentIntent(
            id=intent["id"],
            client_secret=intent.get("client_secret"),
            status=intent.get("status", "unknown"),
            metadata=dict(intent.get("metadata", {})),
        )

    def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntent:
        if self._stripe is None:
            raise StripeClientError("Stripe SDK is not installed")
        try:
            intent = self._stripe.PaymentIntent.confirm(payment_intent_id)
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Failed to confirm payment intent") from exc
        return PaymentIntent(
            id=intent["id"],
            client_secret=intent.get("client_secret"),
            status=intent.get("status", "unknown"),
            metadata=dict(intent.get("metadata", {})),
        )

    def construct_event(self, payload: bytes, signature: str) -> Any:
        if not self._webhook_secret:
            raise StripeClientError("Webhook secret is not configured")
        if self._stripe is None:
            raise StripeClientError("Stripe SDK is not installed")
        try:
            event = self._stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self._webhook_secret,
            )
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Invalid webhook signature") from exc
        return event

    def retrieve_payment_intent(self, payment_intent_id: str) -> PaymentIntent:
        if self._stripe is None:
            raise StripeClientError("Stripe SDK is not installed")
        try:
            intent = self._stripe.PaymentIntent.retrieve(payment_intent_id)
        except Exception as exc:  # pragma: no cover
            raise StripeClientError("Failed to retrieve payment intent") from exc
        return PaymentIntent(
            id=intent["id"],
            client_secret=intent.get("client_secret"),
            status=intent.get("status", "unknown"),
            metadata=dict(intent.get("metadata", {})),
        )
