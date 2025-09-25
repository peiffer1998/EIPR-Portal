"""Thin wrapper around Stripe operations with local fallbacks."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.core.settings import get_payment_settings

try:  # pragma: no cover - exercised when stripe is available
    import stripe  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - deterministic fallback
    stripe = None  # type: ignore


@dataclass(slots=True)
class PaymentIntent:
    """Simplified representation of a Stripe PaymentIntent."""

    id: str
    client_secret: str
    amount: int
    currency: str
    status: str
    metadata: dict[str, Any]


# In-memory fallback store used when the stripe SDK is not available.
_INTENT_STORE: dict[str, PaymentIntent] = {}
_IDEMPOTENCY_STORE: dict[str, str] = {}


def _to_cents(amount: Decimal) -> int:
    quantized = amount.quantize(Decimal("0.01"))
    return int((quantized * 100).to_integral_value())


def _ensure_api_key() -> None:
    settings = get_payment_settings()
    if stripe is not None and settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key


def _generate_id(prefix: str) -> str:
    token = uuid4().hex
    return f"{prefix}_{token}"


def _generate_client_secret(intent_id: str) -> str:
    suffix = "".join(random.choices(string.ascii_letters + string.digits, k=24))
    return f"{intent_id}_secret_{suffix}"


def create_payment_intent(
    *,
    invoice_id: UUID,
    amount: Decimal,
    currency: str = "usd",
    customer_email: str | None = None,
    idempotency_key: str | None = None,
) -> PaymentIntent:
    """Create (or reuse) a PaymentIntent for an invoice."""

    _ensure_api_key()
    cents = _to_cents(amount)
    metadata = {"invoice_id": str(invoice_id)}

    if stripe is not None:
        kwargs = {
            "amount": cents,
            "currency": currency,
            "metadata": metadata,
        }
        if customer_email:
            kwargs["receipt_email"] = customer_email
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key
        intent = stripe.PaymentIntent.create(**kwargs)  # type: ignore[misc]
        return PaymentIntent(
            id=intent["id"],
            client_secret=intent["client_secret"],
            amount=intent["amount"],
            currency=intent["currency"],
            status=intent["status"],
            metadata=dict(intent.get("metadata", {})),
        )

    # Fallback: emulate minimal PaymentIntent behaviour.
    if idempotency_key and idempotency_key in _IDEMPOTENCY_STORE:
        intent_id = _IDEMPOTENCY_STORE[idempotency_key]
        intent = _INTENT_STORE[intent_id]
        _INTENT_STORE[intent_id] = PaymentIntent(
            id=intent.id,
            client_secret=intent.client_secret,
            amount=cents,
            currency=currency,
            status=intent.status,
            metadata=metadata,
        )
        return _INTENT_STORE[intent_id]

    intent_id = _generate_id("pi")
    client_secret = _generate_client_secret(intent_id)
    payment_intent = PaymentIntent(
        id=intent_id,
        client_secret=client_secret,
        amount=cents,
        currency=currency,
        status="requires_payment_method",
        metadata=metadata,
    )
    _INTENT_STORE[intent_id] = payment_intent
    if idempotency_key:
        _IDEMPOTENCY_STORE[idempotency_key] = intent_id
    return payment_intent


def retrieve_payment_intent(payment_intent_id: str) -> PaymentIntent:
    """Retrieve a PaymentIntent, using Stripe if available."""

    _ensure_api_key()
    if stripe is not None:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)  # type: ignore[misc]
        return PaymentIntent(
            id=intent["id"],
            client_secret=intent.get("client_secret", ""),
            amount=intent["amount"],
            currency=intent["currency"],
            status=intent["status"],
            metadata=dict(intent.get("metadata", {})),
        )

    if payment_intent_id not in _INTENT_STORE:
        raise ValueError("PaymentIntent not found")
    return _INTENT_STORE[payment_intent_id]


def refund_charge(
    payment_intent_id: str, amount: Decimal | None = None
) -> dict[str, Any]:
    """Issue a refund for the charge associated with the payment intent."""

    _ensure_api_key()
    cents = _to_cents(amount) if amount is not None else None

    if stripe is not None:
        kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
        if cents is not None:
            kwargs["amount"] = cents
        refund = stripe.Refund.create(**kwargs)  # type: ignore[misc]
        return {"status": refund["status"], "amount": refund.get("amount")}

    intent = retrieve_payment_intent(payment_intent_id)
    new_status = "refunded"
    if cents is not None and cents < intent.amount:
        new_status = "partial_refund"
    _INTENT_STORE[payment_intent_id] = PaymentIntent(
        id=intent.id,
        client_secret=intent.client_secret,
        amount=intent.amount,
        currency=intent.currency,
        status=new_status,
        metadata=intent.metadata,
    )
    return {"status": new_status, "amount": cents or intent.amount}
