"""Stripe SDK wrapper with deterministic fallbacks."""

from __future__ import annotations

import importlib
import random
import string
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
    """Wrapper around the Stripe SDK with optional local fallbacks."""

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
        self._intent_store: dict[str, PaymentIntent] = {}
        self._idempotency_store: dict[str, str] = {}
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

    def _idempotency_key(self, seed: str | uuid.UUID | None) -> str | None:
        if seed is None:
            return None
        return f"{self._idempotency_prefix}_{seed}"

    @staticmethod
    def _to_cents(amount: Decimal) -> int:
        quantized = amount.quantize(Decimal("0.01"))
        return int((quantized * 100).to_integral_value())

    def _fallback_generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    def _fallback_client_secret(self, intent_id: str) -> str:
        suffix = "".join(random.choices(string.ascii_letters + string.digits, k=24))
        return f"{intent_id}_secret_{suffix}"

    def create_payment_intent(
        self,
        *,
        amount: Decimal,
        invoice_id: uuid.UUID,
        currency: str = "usd",
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        idempotency_seed: str | uuid.UUID | None = None,
    ) -> PaymentIntent:
        metadata = dict(metadata or {})
        metadata.setdefault("invoice_id", str(invoice_id))
        cents = self._to_cents(amount)

        if self._stripe is None:
            key = self._idempotency_key(idempotency_seed)
            if key and key in self._idempotency_store:
                intent_id = self._idempotency_store[key]
                intent = self._intent_store[intent_id]
                updated = PaymentIntent(
                    id=intent.id,
                    client_secret=intent.client_secret,
                    status="requires_payment_method",
                    metadata=metadata,
                )
                self._intent_store[intent_id] = updated
                return updated

            intent_id = self._fallback_generate_id("pi")
            client_secret = self._fallback_client_secret(intent_id)
            payment_intent = PaymentIntent(
                id=intent_id,
                client_secret=client_secret,
                status="requires_payment_method",
                metadata=metadata,
            )
            self._intent_store[intent_id] = payment_intent
            if key:
                self._idempotency_store[key] = intent_id
            return payment_intent

        kwargs: dict[str, Any] = {
            "amount": cents,
            "currency": currency,
            "metadata": metadata,
            "confirmation_method": "manual",
            "confirm": False,
        }
        if self._test_mode:
            kwargs.setdefault("payment_method_types", ["card"])
        if customer_email:
            kwargs["receipt_email"] = customer_email

        try:
            intent = self._stripe.PaymentIntent.create(
                **kwargs,
                idempotency_key=self._idempotency_key(idempotency_seed),
            )
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Failed to create payment intent") from exc
        intent_data = cast(dict[str, Any], intent)
        metadata_dict = cast(dict[str, Any], intent_data.get("metadata", {}))
        return PaymentIntent(
            id=str(intent_data.get("id")),
            client_secret=cast(str | None, intent_data.get("client_secret")),
            status=str(intent_data.get("status", "unknown")),
            metadata=dict(metadata_dict),
        )

    def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntent:
        if self._stripe is None:
            intent = self._intent_store.get(payment_intent_id)
            if intent is None:
                raise StripeClientError("Payment intent not found")
            confirmed = PaymentIntent(
                id=intent.id,
                client_secret=intent.client_secret,
                status="succeeded",
                metadata=dict(intent.metadata),
            )
            self._intent_store[payment_intent_id] = confirmed
            return confirmed

        try:
            intent = self._stripe.PaymentIntent.confirm(payment_intent_id)
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Failed to confirm payment intent") from exc
        intent_data = cast(dict[str, Any], intent)
        metadata_dict = cast(dict[str, Any], intent_data.get("metadata", {}))
        return PaymentIntent(
            id=str(intent_data.get("id")),
            client_secret=cast(str | None, intent_data.get("client_secret")),
            status=str(intent_data.get("status", "unknown")),
            metadata=dict(metadata_dict),
        )

    def retrieve_payment_intent(self, payment_intent_id: str) -> PaymentIntent:
        if self._stripe is None:
            intent = self._intent_store.get(payment_intent_id)
            if intent is None:
                raise StripeClientError("Payment intent not found")
            return intent
        try:
            intent = self._stripe.PaymentIntent.retrieve(payment_intent_id)
        except Exception as exc:  # pragma: no cover
            raise StripeClientError("Failed to retrieve payment intent") from exc
        intent_data = cast(dict[str, Any], intent)
        metadata_dict = cast(dict[str, Any], intent_data.get("metadata", {}))
        return PaymentIntent(
            id=str(intent_data.get("id")),
            client_secret=cast(str | None, intent_data.get("client_secret")),
            status=str(intent_data.get("status", "unknown")),
            metadata=dict(metadata_dict),
        )

    def refund_payment_intent(
        self, payment_intent_id: str, *, amount: Decimal | None = None
    ) -> dict[str, Any]:
        if self._stripe is None:
            intent = self._intent_store.get(payment_intent_id)
            if intent is None:
                raise StripeClientError("Payment intent not found")
            status = "refunded"
            if amount is not None:
                if amount < Decimal("0"):
                    raise StripeClientError("Invalid refund amount")
                status = "partial_refund"
            updated = PaymentIntent(
                id=intent.id,
                client_secret=intent.client_secret,
                status=status,
                metadata=intent.metadata,
            )
            self._intent_store[payment_intent_id] = updated
            cents = self._to_cents(amount) if amount is not None else None
            return {"status": status, "amount": cents}

        kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
        if amount is not None:
            kwargs["amount"] = self._to_cents(amount)
        try:
            refund = self._stripe.Refund.create(**kwargs)
        except Exception as exc:  # pragma: no cover - surfaced in API error handling
            raise StripeClientError("Failed to refund payment intent") from exc
        return {
            "status": refund.get("status", "unknown"),
            "amount": refund.get("amount"),
        }

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
