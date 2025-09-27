"""QuickBooks Online sales receipt export helper."""

from __future__ import annotations

import csv
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceStatus
from app.models.reservation import Reservation
from app.models.pet import Pet
from app.models.owner_profile import OwnerProfile
from app.security.redact import is_redaction_enabled, mask_name

HEADER = [
    "invoice_id",
    "reservation_id",
    "paid_at",
    "pet_name",
    "owner_name",
    "subtotal",
    "discount_total",
    "tax_total",
    "total_amount",
]


async def export_sales_receipts(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    target_date: date,
    export_dir: Path,
) -> tuple[Path, int]:
    """Write paid invoices for the target date to CSV."""

    export_dir.mkdir(parents=True, exist_ok=True)
    filename = f"sales-receipt-{target_date.isoformat()}.csv"
    destination = export_dir / filename

    start_dt = datetime.combine(target_date, time.min, tzinfo=UTC)
    end_dt = start_dt + timedelta(days=1)

    stmt = (
        select(Invoice)
        .where(
            Invoice.account_id == account_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= start_dt,
            Invoice.paid_at < end_dt,
        )
        .options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user)
        )
        .order_by(Invoice.paid_at.asc())
    )
    result = await session.execute(stmt)
    invoices = list(result.scalars().unique().all())

    redact_enabled = is_redaction_enabled()

    with destination.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(HEADER)
        for invoice in invoices:
            pet_name = None
            owner_name = None
            if invoice.reservation and invoice.reservation.pet:
                pet_name = invoice.reservation.pet.name
                owner_profile = invoice.reservation.pet.owner
                if owner_profile and owner_profile.user:
                    first = owner_profile.user.first_name
                    last = owner_profile.user.last_name
                    if redact_enabled:
                        owner_name = mask_name(first, last)
                    else:
                        owner_name = " ".join(part for part in (first, last) if part)
            writer.writerow(
                [
                    str(invoice.id),
                    str(invoice.reservation_id),
                    invoice.paid_at.isoformat() if invoice.paid_at else "",
                    pet_name or "",
                    owner_name or "",
                    _format_decimal(invoice.subtotal),
                    _format_decimal(invoice.discount_total),
                    _format_decimal(invoice.tax_total),
                    _format_decimal(invoice.total_amount),
                ]
            )

    return destination, len(invoices)


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
