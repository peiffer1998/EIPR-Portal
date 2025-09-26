"""Import Gingr data from MySQL into the EIPR Postgres database."""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import re
import secrets
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pymysql
import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import get_password_hash
from app.models import Account, Location
from app.models.immunization import (
    ImmunizationRecord,
    ImmunizationStatus,
    ImmunizationType,
)
from app.models.owner_profile import OwnerProfile
from app.models.payment import PaymentTransaction, PaymentTransactionStatus
from app.models.pet import Pet, PetType
from app.models.reservation import Reservation, ReservationStatus, ReservationType
from app.models.invoice import Invoice, InvoiceStatus
from app.models.store import PackageCredit, PackageCreditSource
from app.models.user import User, UserRole, UserStatus

LOGGER = logging.getLogger("gingr_import")
DEFAULT_ACCOUNT_NAME = "Eastern Iowa Pet Resort"
DEFAULT_ACCOUNT_SLUG = "eipr"
DEFAULT_LOCATION_NAME = "Main"
DEFAULT_TIMEZONE = "America/Chicago"


@dataclass
class ImportStats:
    name: str
    processed: int = 0
    created: int = 0
    skipped: int = 0
    rejects: list[str] = field(default_factory=list)

    def reject(self, reason: str) -> None:
        self.processed += 1
        self.skipped += 1
        if len(self.rejects) < 10:
            self.rejects.append(reason)

    def create(self) -> None:
        self.processed += 1
        self.created += 1

    def skip(self) -> None:
        self.processed += 1
        self.skipped += 1


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOGGER.addHandler(console)


def get_mysql_connection() -> pymysql.connections.Connection:
    host = os.environ.get("GINGR_MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("GINGR_MYSQL_PORT", "3307"))
    db = os.environ.get("GINGR_MYSQL_DB", "gingr")
    user = os.environ.get("GINGR_MYSQL_USER", "root")
    password = os.environ.get("GINGR_MYSQL_PASSWORD", "rootpass")
    LOGGER.info("Connecting to Gingr MySQL at %s:%s/%s", host, port, db)
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
    )


def get_postgres_session(sync_url: str) -> Session:
    engine = create_engine(sync_url, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return SessionLocal()


def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip().lower()
    return email or None


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+1" + digits[1:]
    if phone.startswith("+"):
        return phone
    return "+" + digits


def parse_date(value: Any) -> Optional[dt.date]:
    if value in (None, "", 0):
        return None
    if isinstance(value, dt.date):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return dt.datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value: Any) -> Optional[dt.datetime]:
    if value in (None, "", 0):
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time())
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError:
        pass
    return None


def pet_type_from_string(raw: Optional[str]) -> PetType:
    if not raw:
        return PetType.OTHER
    lowered = raw.lower()
    if "cat" in lowered:
        return PetType.CAT
    if "dog" in lowered or "canine" in lowered:
        return PetType.DOG
    return PetType.OTHER


def reservation_type_from_string(raw: Optional[str]) -> ReservationType:
    if not raw:
        return ReservationType.OTHER
    lowered = raw.lower()
    if any(key in lowered for key in ("board", "lodg")):
        return ReservationType.BOARDING
    if "day" in lowered:
        return ReservationType.DAYCARE
    if "groom" in lowered:
        return ReservationType.GROOMING
    if "train" in lowered:
        return ReservationType.TRAINING
    return ReservationType.OTHER


def reservation_status_from_string(raw: Optional[str]) -> ReservationStatus:
    if not raw:
        return ReservationStatus.CONFIRMED
    lowered = raw.lower()
    mapping = {
        "requested": ReservationStatus.REQUESTED,
        "pending": ReservationStatus.REQUESTED,
        "accepted": ReservationStatus.ACCEPTED,
        "confirmed": ReservationStatus.CONFIRMED,
        "checked_in": ReservationStatus.CHECKED_IN,
        "checkin": ReservationStatus.CHECKED_IN,
        "checked_out": ReservationStatus.CHECKED_OUT,
        "checkout": ReservationStatus.CHECKED_OUT,
        "cancel": ReservationStatus.CANCELED,
        "void": ReservationStatus.CANCELED,
    }
    for key, status in mapping.items():
        if key in lowered:
            return status
    return ReservationStatus.CONFIRMED


def payment_status_from_string(raw: Optional[str]) -> PaymentTransactionStatus:
    if not raw:
        return PaymentTransactionStatus.SUCCEEDED
    lowered = raw.lower()
    mapping = {
        "success": PaymentTransactionStatus.SUCCEEDED,
        "complete": PaymentTransactionStatus.SUCCEEDED,
        "paid": PaymentTransactionStatus.SUCCEEDED,
        "pending": PaymentTransactionStatus.PROCESSING,
        "hold": PaymentTransactionStatus.PROCESSING,
        "fail": PaymentTransactionStatus.FAILED,
        "declin": PaymentTransactionStatus.FAILED,
        "cancel": PaymentTransactionStatus.CANCELED,
        "refund": PaymentTransactionStatus.REFUNDED,
    }
    for key, status in mapping.items():
        if key in lowered:
            return status
    return PaymentTransactionStatus.SUCCEEDED


@dataclass
class ImportContext:
    session: Session
    mysql: pymysql.connections.Connection
    mapping: Dict[str, Any]
    dry_run: bool
    limit: Optional[int]
    since: Optional[dt.datetime]
    account: Account
    location: Location
    owners_by_external: Dict[str, OwnerProfile] = field(default_factory=dict)
    pets_by_external: Dict[str, Pet] = field(default_factory=dict)
    reservations_by_external: Dict[str, Reservation] = field(default_factory=dict)
    invoices_by_external: Dict[str, Invoice] = field(default_factory=dict)


def ensure_account_and_location(session: Session) -> tuple[Account, Location]:
    account = session.execute(
        select(Account).where(Account.slug == DEFAULT_ACCOUNT_SLUG)
    ).scalar_one_or_none()
    if account is None:
        account = Account(name=DEFAULT_ACCOUNT_NAME, slug=DEFAULT_ACCOUNT_SLUG)
        session.add(account)
        session.commit()
        LOGGER.info("Created default account '%s'", DEFAULT_ACCOUNT_NAME)

    location = session.execute(
        select(Location).where(Location.account_id == account.id)
    ).scalar_one_or_none()
    if location is None:
        location = Location(
            account_id=account.id,
            name=DEFAULT_LOCATION_NAME,
            timezone=DEFAULT_TIMEZONE,
        )
        session.add(location)
        session.commit()
        LOGGER.info("Created default location '%s'", DEFAULT_LOCATION_NAME)

    return account, location


def load_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def build_select_clause(target: str, mapping: Dict[str, Any]) -> tuple[str, list[str]]:
    entry = mapping.get(target) or {}
    table = entry.get("table")
    columns: Dict[str, Optional[str]] = entry.get("columns", {})
    selected_columns = [col for col in columns.values() if col]
    if not table or not selected_columns:
        raise ValueError(f"Mapping for {target} is incomplete: {entry}")
    return table, selected_columns


def fetch_rows(
    mysql: pymysql.connections.Connection,
    table: str,
    columns: Iterable[str],
    limit: Optional[int],
    since: Optional[dt.datetime],
    since_column: Optional[str],
) -> Iterable[dict[str, Any]]:
    cols = ", ".join(f"`{c}`" for c in columns)
    sql = f"SELECT {cols} FROM `{table}`"
    params: list[Any] = []
    if since and since_column:
        sql += f" WHERE `{since_column}` >= %s"
        params.append(since)
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with mysql.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            yield row


def import_owners(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("owners")
    entry = ctx.mapping.get("owners", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    first_col = columns.get("first_name")
    last_col = columns.get("last_name")
    email_col = columns.get("email")
    phone_col = columns.get("phone")
    updated_col = columns.get("updated_at")

    if not table or not id_col:
        LOGGER.warning("Skipping owners import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [id_col, first_col, last_col, email_col, phone_col, updated_col]
        if col
    ]
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        if not external_id:
            stats.reject("owner missing id")
            continue
        if ctx.session.execute(
            select(OwnerProfile).where(OwnerProfile.external_id == external_id)
        ).scalar_one_or_none():
            stats.skip()
            continue

        if ctx.dry_run:
            stats.skip()
            continue

        first_name = (
            (row.get(first_col) or "Customer").strip() if first_col else "Customer"
        )
        last_name = (
            (row.get(last_col) or external_id).strip() if last_col else external_id
        )
        email = normalize_email(row.get(email_col) if email_col else None)
        phone = normalize_phone(row.get(phone_col) if phone_col else None)

        if email:
            existing_user = ctx.session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            if existing_user:
                # ensure email uniqueness by appending tag
                unique_suffix = secrets.token_hex(4)
                email = f"{existing_user.email.split('@')[0]}+{unique_suffix}@{existing_user.email.split('@')[1]}"

        password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            account_id=ctx.account.id,
            email=email or f"imported+{external_id}@example.com",
            hashed_password=password,
            first_name=first_name or "Customer",
            last_name=last_name or "Imported",
            phone_number=phone,
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
            is_primary_contact=True,
        )
        owner = OwnerProfile(
            user=user,
            external_id=external_id,
            email_opt_in=True,
            sms_opt_in=bool(phone),
        )
        ctx.session.add(owner)
        ctx.owners_by_external[external_id] = owner
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Owners: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def import_pets(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("pets")
    entry = ctx.mapping.get("pets", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    owner_col = columns.get("owner_id")
    name_col = columns.get("name")
    species_col = columns.get("species")
    breed_col = columns.get("breed")
    color_col = columns.get("color")
    dob_col = columns.get("dob")
    updated_col = columns.get("updated_at")

    if not table or not id_col or not owner_col or not name_col:
        LOGGER.warning("Skipping pets import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [
            id_col,
            owner_col,
            name_col,
            species_col,
            breed_col,
            color_col,
            dob_col,
            updated_col,
        ]
        if col
    ]
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        owner_external = (
            str(row.get(owner_col)) if row.get(owner_col) is not None else None
        )
        if not external_id or not owner_external:
            stats.reject("pet missing id or owner id")
            continue
        owner = ctx.session.execute(
            select(OwnerProfile).where(OwnerProfile.external_id == owner_external)
        ).scalar_one_or_none()
        if not owner:
            stats.reject(f"owner {owner_external} not found for pet {external_id}")
            continue
        if ctx.session.execute(
            select(Pet).where(Pet.external_id == external_id)
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        pet = Pet(
            owner_id=owner.id,
            home_location_id=ctx.location.id,
            name=(row.get(name_col) or "Pet").strip(),
            pet_type=pet_type_from_string(
                row.get(species_col) if species_col else None
            ),
            breed=(row.get(breed_col) or None) if breed_col else None,
            color=(row.get(color_col) or None) if color_col else None,
            date_of_birth=parse_date(row.get(dob_col) if dob_col else None),
            external_id=external_id,
        )
        ctx.session.add(pet)
        ctx.pets_by_external[external_id] = pet
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Pets: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def ensure_immunization_type(
    session: Session, account_id: Any, name: str
) -> ImmunizationType:
    name_clean = name.strip() if name else "General"
    type_obj = session.execute(
        select(ImmunizationType).where(
            ImmunizationType.account_id == account_id,
            ImmunizationType.name == name_clean,
        )
    ).scalar_one_or_none()
    if type_obj is None:
        type_obj = ImmunizationType(
            account_id=account_id,
            name=name_clean,
            required=False,
        )
        session.add(type_obj)
        session.commit()
    return type_obj


def import_immunizations(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("immunizations")
    entry = ctx.mapping.get("immunizations", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    pet_col = columns.get("pet_id")
    vaccine_col = columns.get("vaccine")
    issued_col = columns.get("issued_on")
    expires_col = columns.get("expires_on")
    status_col = columns.get("status")

    if not table or not id_col or not pet_col or not vaccine_col:
        LOGGER.warning("Skipping immunizations import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [id_col, pet_col, vaccine_col, issued_col, expires_col, status_col]
        if col
    ]
    for row in fetch_rows(ctx.mysql, table, select_columns, ctx.limit, None, None):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        pet_external = str(row.get(pet_col)) if row.get(pet_col) is not None else None
        if not external_id or not pet_external:
            stats.reject("immunization missing id or pet id")
            continue
        pet = ctx.session.execute(
            select(Pet).where(Pet.external_id == pet_external)
        ).scalar_one_or_none()
        if not pet:
            stats.reject(f"pet {pet_external} missing for immunization {external_id}")
            continue
        if ctx.session.execute(
            select(ImmunizationRecord).where(
                ImmunizationRecord.external_id == external_id
            )
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        vaccine_name = str(row.get(vaccine_col) or "General")
        type_obj = ensure_immunization_type(ctx.session, ctx.account.id, vaccine_name)
        issued_on = parse_date(row.get(issued_col)) or dt.date.today()
        expires_on = parse_date(row.get(expires_col))
        status_raw = (row.get(status_col) or "").lower() if status_col else ""
        status = ImmunizationStatus.CURRENT
        if "expire" in status_raw:
            status = (
                ImmunizationStatus.EXPIRING
                if "ing" in status_raw
                else ImmunizationStatus.EXPIRED
            )
        elif "pending" in status_raw:
            status = ImmunizationStatus.PENDING

        record = ImmunizationRecord(
            account_id=ctx.account.id,
            pet_id=pet.id,
            type_id=type_obj.id,
            issued_on=issued_on,
            expires_on=expires_on,
            status=status,
            notes=f"Imported from Gingr ID {external_id}",
        )
        ctx.session.add(record)
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Immunizations: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def import_reservations(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("reservations")
    entry = ctx.mapping.get("reservations", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    pet_col = columns.get("pet_id")
    start_col = columns.get("start_at")
    end_col = columns.get("end_at")
    status_col = columns.get("status")
    type_col = columns.get("type")
    location_col = columns.get("location_id")
    notes_col = columns.get("notes")
    updated_col = columns.get("updated_at")

    if not table or not id_col or not pet_col or not start_col or not end_col:
        LOGGER.warning("Skipping reservations import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [
            id_col,
            pet_col,
            start_col,
            end_col,
            status_col,
            type_col,
            location_col,
            notes_col,
            updated_col,
        ]
        if col
    ]
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        pet_external = str(row.get(pet_col)) if row.get(pet_col) is not None else None
        if not external_id or not pet_external:
            stats.reject("reservation missing id or pet id")
            continue
        pet = ctx.session.execute(
            select(Pet).where(Pet.external_id == pet_external)
        ).scalar_one_or_none()
        if not pet:
            stats.reject(f"pet {pet_external} missing for reservation {external_id}")
            continue
        if ctx.session.execute(
            select(Reservation).where(Reservation.external_id == external_id)
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        start_at = parse_datetime(row.get(start_col)) or dt.datetime.utcnow()
        end_at = parse_datetime(row.get(end_col)) or start_at
        status = reservation_status_from_string(
            row.get(status_col) if status_col else None
        )
        res_type = reservation_type_from_string(row.get(type_col) if type_col else None)

        reservation = Reservation(
            account_id=ctx.account.id,
            location_id=ctx.location.id,
            pet_id=pet.id,
            reservation_type=res_type,
            status=status,
            start_at=start_at,
            end_at=end_at,
            base_rate=Decimal("0"),
            notes=row.get(notes_col) if notes_col else None,
            external_id=external_id,
        )
        ctx.session.add(reservation)
        ctx.reservations_by_external[external_id] = reservation
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Reservations: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def import_invoices(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("invoices")
    entry = ctx.mapping.get("invoices", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    reservation_col = columns.get("reservation_id")
    total_col = columns.get("total")
    balance_col = columns.get("balance")
    status_col = columns.get("status")
    created_col = columns.get("created_at")
    updated_col = columns.get("updated_at")

    if not table or not id_col or not reservation_col:
        LOGGER.warning("Skipping invoices import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [
            id_col,
            reservation_col,
            total_col,
            balance_col,
            status_col,
            created_col,
            updated_col,
        ]
        if col
    ]
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        reservation_external = (
            str(row.get(reservation_col))
            if row.get(reservation_col) is not None
            else None
        )
        if not external_id or not reservation_external:
            stats.reject("invoice missing id or reservation id")
            continue
        reservation = ctx.session.execute(
            select(Reservation).where(Reservation.external_id == reservation_external)
        ).scalar_one_or_none()
        if not reservation:
            stats.reject(
                f"reservation {reservation_external} missing for invoice {external_id}"
            )
            continue
        if ctx.session.execute(
            select(Invoice).where(Invoice.external_id == external_id)
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        total = Decimal(str(row.get(total_col) or "0")) if total_col else Decimal("0")
        balance = (
            Decimal(str(row.get(balance_col) or "0")) if balance_col else Decimal("0")
        )
        created_at = parse_datetime(row.get(created_col)) if created_col else None

        invoice = Invoice(
            account_id=ctx.account.id,
            reservation_id=reservation.id,
            status=(
                InvoiceStatus.PAID
                if balance <= Decimal("0.01")
                else InvoiceStatus.PENDING
            ),
            subtotal=total,
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            credits_total=max(Decimal("0"), total - balance),
            total=total,
            total_amount=total,
            paid_at=created_at if balance <= Decimal("0.01") else None,
            external_id=external_id,
        )
        ctx.session.add(invoice)
        ctx.invoices_by_external[external_id] = invoice
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Invoices: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def import_payments(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("payments")
    entry = ctx.mapping.get("payments", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    invoice_col = columns.get("invoice_id")
    amount_col = columns.get("amount")
    status_col = columns.get("status")
    method_col = columns.get("method")
    processed_col = columns.get("processed_at")

    if not table or not id_col or not invoice_col or not amount_col:
        LOGGER.warning("Skipping payments import: mapping incomplete")
        return stats

    select_columns = [
        col
        for col in [
            id_col,
            invoice_col,
            amount_col,
            status_col,
            method_col,
            processed_col,
        ]
        if col
    ]
    for row in fetch_rows(ctx.mysql, table, select_columns, ctx.limit, None, None):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        invoice_external = (
            str(row.get(invoice_col)) if row.get(invoice_col) is not None else None
        )
        if not external_id or not invoice_external:
            stats.reject("payment missing id or invoice id")
            continue
        invoice = ctx.session.execute(
            select(Invoice).where(Invoice.external_id == invoice_external)
        ).scalar_one_or_none()
        if not invoice:
            stats.reject(
                f"invoice {invoice_external} missing for payment {external_id}"
            )
            continue
        if ctx.session.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.external_id == external_id
            )
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        amount = Decimal(str(row.get(amount_col) or "0"))
        status = payment_status_from_string(row.get(status_col) if status_col else None)
        processed_at = parse_datetime(row.get(processed_col)) or dt.datetime.utcnow()
        provider = (row.get(method_col) or "stripe").lower() if method_col else "stripe"

        payment = PaymentTransaction(
            account_id=ctx.account.id,
            invoice_id=invoice.id,
            owner_id=invoice.reservation.pet.owner.id,
            provider=provider[:32],
            amount=amount,
            currency="usd",
            status=status,
            external_id=external_id,
            failure_reason=None,
        )
        payment.created_at = processed_at
        ctx.session.add(payment)
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Payments: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def import_package_credits(ctx: ImportContext) -> ImportStats:
    stats = ImportStats("packages")
    entry = ctx.mapping.get("packages", {})
    table = entry.get("table")
    columns = entry.get("columns", {})
    id_col = columns.get("id")
    owner_col = columns.get("owner_id")
    credits_col = columns.get("credits")
    name_col = columns.get("name")
    updated_col = columns.get("updated_at")

    if not table or not id_col or not owner_col or not credits_col:
        LOGGER.warning("Skipping packages import: mapping incomplete")
        return stats

    select_columns = [
        col for col in [id_col, owner_col, credits_col, name_col, updated_col] if col
    ]
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        external_id = str(row.get(id_col)) if row.get(id_col) is not None else None
        owner_external = (
            str(row.get(owner_col)) if row.get(owner_col) is not None else None
        )
        if not external_id or not owner_external:
            stats.reject("package credit missing id or owner id")
            continue
        owner = ctx.session.execute(
            select(OwnerProfile).where(OwnerProfile.external_id == owner_external)
        ).scalar_one_or_none()
        if not owner:
            stats.reject(f"owner {owner_external} missing for package {external_id}")
            continue
        if ctx.session.execute(
            select(PackageCredit).where(PackageCredit.external_id == external_id)
        ).scalar_one_or_none():
            stats.skip()
            continue
        if ctx.dry_run:
            stats.skip()
            continue

        credits_raw = row.get(credits_col)
        credits = int(credits_raw) if credits_raw not in (None, "") else 0
        package = PackageCredit(
            account_id=ctx.account.id,
            owner_id=owner.id,
            package_type_id=None,  # will be null until manual mapping
            credits=credits,
            source=PackageCreditSource.ADJUST,
            invoice_id=None,
            reservation_id=None,
            note=(row.get(name_col) if name_col else None),
            external_id=external_id,
        )
        ctx.session.add(package)
        stats.create()

    if not ctx.dry_run:
        ctx.session.commit()
    LOGGER.info(
        "Package credits: processed=%s created=%s skipped=%s",
        stats.processed,
        stats.created,
        stats.skipped,
    )
    return stats


def run_import(ctx: ImportContext) -> list[ImportStats]:
    stats_list = []
    stats_list.append(import_owners(ctx))
    stats_list.append(import_pets(ctx))
    stats_list.append(import_immunizations(ctx))
    stats_list.append(import_reservations(ctx))
    stats_list.append(import_invoices(ctx))
    stats_list.append(import_payments(ctx))
    stats_list.append(import_package_credits(ctx))
    return stats_list


def parse_since(since_str: Optional[str]) -> Optional[dt.datetime]:
    if not since_str:
        return None
    try:
        return dt.datetime.fromisoformat(since_str)
    except ValueError:
        LOGGER.warning("Invalid since value '%s'; ignoring", since_str)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Gingr data")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="Collect counts without writing data"
    )
    mode.add_argument("--run", action="store_true", help="Perform the import")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows per entity")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only import rows updated since ISO timestamp",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("backend/scripts/gingr_mapping.yaml"),
        help="Path to mapping YAML produced by gingr_automap",
    )
    args = parser.parse_args()

    dry_run = args.dry_run or not args.run
    limit = args.limit
    since = parse_since(args.since)

    configure_logging(Path("imports/etl.log"))

    try:
        mapping = load_mapping(args.mapping)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc

    try:
        mysql = get_mysql_connection()
    except Exception as exc:  # pragma: no cover - environment specific
        LOGGER.error("Failed to connect to Gingr MySQL: %s", exc)
        raise SystemExit(2) from exc

    sync_url = os.environ.get("SYNC_DATABASE_URL")
    if not sync_url:
        LOGGER.error("SYNC_DATABASE_URL environment variable is required")
        raise SystemExit(3)

    session = get_postgres_session(sync_url)
    account, location = ensure_account_and_location(session)

    ctx = ImportContext(
        session=session,
        mysql=mysql,
        mapping=mapping,
        dry_run=dry_run,
        limit=limit,
        since=since,
        account=account,
        location=location,
    )

    stats_list = run_import(ctx)

    mysql.close()
    if not dry_run:
        session.commit()
    session.close()

    total_processed = sum(stat.processed for stat in stats_list)
    total_rejected = sum(stat.skipped for stat in stats_list) - sum(
        stat.created for stat in stats_list
    )
    reject_ratio = (total_rejected / total_processed) if total_processed else 0

    LOGGER.info("Import summary:")
    for stat in stats_list:
        LOGGER.info(
            "  %-15s processed=%-5s created=%-5s skipped=%-5s",
            stat.name,
            stat.processed,
            stat.created,
            stat.skipped,
        )
        if stat.rejects:
            LOGGER.info("    sample rejects: %s", stat.rejects)

    if reject_ratio > 0.01:
        LOGGER.error("Reject ratio %.2f%% exceeds threshold", reject_ratio * 100)
        raise SystemExit(4)

    LOGGER.info("Import completed (mode=%s)", "dry-run" if dry_run else "run")


if __name__ == "__main__":
    main()
