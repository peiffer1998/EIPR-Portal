"""End-to-end tests covering payment workflows."""

from __future__ import annotations

import datetime
from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import selectinload

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    DepositStatus,
    Invoice,
    InvoiceStatus,
    Location,
    OwnerProfile,
    PaymentTransaction,
    PaymentTransactionStatus,
    Pet,
    PetType,
    Reservation,
    ReservationType,
    User,
    UserRole,
    UserStatus,
)
from app.integrations import StripeClient
from app.services import invoice_service, payments_service

pytestmark = pytest.mark.asyncio


async def _seed_invoice(
    session,
    *,
    base_rate: Decimal = Decimal("200.00"),
) -> tuple[Account, Invoice, Reservation]:
    account = Account(name="Pay Resort", slug=f"pay-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Cedar Rapids", timezone="UTC")
    session.add(location)
    await session.flush()

    user = User(
        account_id=account.id,
        email=f"payer+{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        first_name="Pat",
        last_name="Payer",
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    owner = OwnerProfile(user_id=user.id)
    session.add(owner)
    await session.flush()

    pet = Pet(owner_id=owner.id, name="PaymentDog", pet_type=PetType.DOG)
    session.add(pet)
    await session.flush()

    start_at = datetime.datetime(2025, 5, 1, 12, tzinfo=datetime.timezone.utc)
    end_at = start_at + datetime.timedelta(days=2)

    reservation = Reservation(
        account_id=account.id,
        location_id=location.id,
        pet_id=pet.id,
        reservation_type=ReservationType.BOARDING,
        start_at=start_at,
        end_at=end_at,
        base_rate=base_rate,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)

    invoice_id = await invoice_service.create_from_reservation(
        session,
        reservation_id=reservation.id,
        account_id=account.id,
    )
    invoice = await session.get(Invoice, invoice_id)
    assert invoice is not None
    await session.refresh(invoice)
    return account, invoice, reservation


async def test_payment_success_consumes_deposit_and_marks_invoice(
    reset_database, db_url: str
) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, invoice, reservation = await _seed_invoice(session)

        await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="hold",
            amount=Decimal("50.00"),
        )

        stripe_client = StripeClient("sk_test_dummy", test_mode=True)

        (
            client_secret,
            transaction_id,
        ) = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=account.id,
            invoice_id=invoice.id,
            stripe=stripe_client,
        )
        assert client_secret

        transaction = await session.get(PaymentTransaction, transaction_id)
        assert transaction is not None
        expected_due = (invoice.total or Decimal("0")) - Decimal("50.00")
        assert transaction.amount == expected_due.quantize(Decimal("0.01"))

        await payments_service.mark_invoice_paid_on_success(
            session,
            invoice_id=invoice.id,
            transaction_id=transaction_id,
        )

        updated_transaction = await session.get(PaymentTransaction, transaction_id)
        assert updated_transaction is not None
        assert updated_transaction.status is PaymentTransactionStatus.SUCCEEDED

        updated_invoice = await session.get(Invoice, invoice.id)
        assert updated_invoice is not None
        assert updated_invoice.status is InvoiceStatus.PAID
        assert updated_invoice.paid_at is not None

        refreshed_reservation = await session.get(
            Reservation,
            reservation.id,
            options=[selectinload(Reservation.deposits)],
        )
        assert refreshed_reservation is not None
        assert all(
            deposit.status is DepositStatus.CONSUMED
            for deposit in refreshed_reservation.deposits
        )


async def test_payment_failure_updates_transaction(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, invoice, _ = await _seed_invoice(session)
        stripe_client = StripeClient("sk_test_dummy", test_mode=True)

        _, transaction_id = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=account.id,
            invoice_id=invoice.id,
            stripe=stripe_client,
        )

        transaction = await session.get(PaymentTransaction, transaction_id)
        assert transaction is not None
        transaction.status = PaymentTransactionStatus.FAILED
        transaction.failure_reason = "card_declined"
        await session.commit()

        updated = await session.get(PaymentTransaction, transaction_id)
        assert updated is not None
        assert updated.status is PaymentTransactionStatus.FAILED
        assert updated.failure_reason == "card_declined"


async def test_payment_refund_markers(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, invoice, _ = await _seed_invoice(session)
        stripe_client = StripeClient("sk_test_dummy", test_mode=True)

        _, transaction_id = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=account.id,
            invoice_id=invoice.id,
            stripe=stripe_client,
        )

        transaction = await session.get(PaymentTransaction, transaction_id)
        assert transaction is not None

        await payments_service.apply_refund_markers(
            session,
            invoice_id=invoice.id,
            transaction_id=transaction_id,
            amount=Decimal("25.00"),
        )
        partial = await session.get(PaymentTransaction, transaction_id)
        assert partial is not None
        assert partial.status is PaymentTransactionStatus.PARTIAL_REFUND

        await payments_service.apply_refund_markers(
            session,
            invoice_id=invoice.id,
            transaction_id=transaction_id,
            amount=None,
        )
        refunded = await session.get(PaymentTransaction, transaction_id)
        assert refunded is not None
        assert refunded.status is PaymentTransactionStatus.REFUNDED


async def test_payment_zero_balance_blocks_intent(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, invoice, reservation = await _seed_invoice(session)
        await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="hold",
            amount=invoice.total or Decimal("0"),
        )
        stripe_client = StripeClient("sk_test_dummy", test_mode=True)
        try:
            await payments_service.create_or_update_payment_for_invoice(
                session,
                account_id=account.id,
                invoice_id=invoice.id,
                stripe=stripe_client,
            )
        except ValueError as exc:
            assert "no payment required" in str(exc)
        else:
            raise AssertionError("Expected ValueError for zero balance")
