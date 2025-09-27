"""Import Gingr data from MySQL into the EIPR Postgres database."""

# ruff: noqa: E402  # allow path/bootstrap tweaks before app imports

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
import secrets
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional

import pymysql
import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

_allowlist = os.environ.get("CORS_ALLOWLIST")
if _allowlist and not _allowlist.strip().startswith("["):
    cleaned = [origin.strip() for origin in _allowlist.split(",") if origin.strip()]
    os.environ["CORS_ALLOWLIST"] = json.dumps(cleaned)

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
from app.models.store import (
    PackageApplicationType,
    PackageCredit,
    PackageCreditSource,
    PackageType,
)
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


def resolve_sync_database_url() -> Optional[str]:
    """Return a synchronous SQLAlchemy URL, falling back to DATABASE_URL when needed."""

    sync_url = os.environ.get("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None

    try:
        url = make_url(database_url)
    except Exception:  # pragma: no cover - defensive parsing
        LOGGER.warning("DATABASE_URL was set but could not be parsed; using raw value")
        return database_url

    driver = url.drivername
    if driver.endswith("+asyncpg"):
        driver = driver[: -len("+asyncpg")] + "+psycopg"
    elif driver.endswith("+psycopg_async"):
        driver = driver[: -len("+psycopg_async")] + "+psycopg"

    url = url.set(drivername=driver)
    LOGGER.info("Resolved sync database URL from DATABASE_URL driver=%s", driver)
    return str(url)


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


def epoch_to_datetime(value: Any) -> Optional[dt.datetime]:
    """Convert epoch seconds (int or str) to timezone-aware UTC datetime."""

    if value in (None, "", 0):
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    try:
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError):  # pragma: no cover - platform specific
        return None


def epoch_to_date(value: Any) -> Optional[dt.date]:
    dt_value = epoch_to_datetime(value)
    return dt_value.date() if dt_value else None


def to_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:  # pragma: no cover - defensive
        return Decimal(default)


def safe_int(value: Any) -> int | None:
    """Attempt to coerce a value to ``int`` returning ``None`` on failure."""

    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    owners_by_external: Dict[str, OwnerProfile | SimpleNamespace] = field(
        default_factory=dict
    )
    pets_by_external: Dict[str, Pet | SimpleNamespace] = field(default_factory=dict)
    reservations_by_external: Dict[str, Reservation | SimpleNamespace] = field(
        default_factory=dict
    )
    invoices_by_external: Dict[str, Invoice | SimpleNamespace] = field(
        default_factory=dict
    )
    species_map: Dict[int, str] = field(default_factory=dict)
    breed_map: Dict[int, str] = field(default_factory=dict)
    reservation_type_map: Dict[int, str] = field(default_factory=dict)
    immunization_type_map: Dict[int, str] = field(default_factory=dict)
    payment_method_map: Dict[int, str] = field(default_factory=dict)
    package_definitions: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    package_types_cache: Dict[int, Any] = field(default_factory=dict)
    pos_transaction_meta: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    pos_items_by_transaction: Dict[int, list[Dict[str, Any]]] = field(
        default_factory=dict
    )
    pos_item_details: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    pos_reservations: Dict[int, set[int]] = field(default_factory=dict)
    reservation_items: Dict[int, list[Dict[str, Any]]] = field(default_factory=dict)
    payment_allocations: Dict[int, list[Dict[str, Any]]] = field(default_factory=dict)
    invoice_payment_totals: Dict[str, Decimal] = field(default_factory=dict)
    placeholder_pets: Dict[str, Pet] = field(default_factory=dict)
    pos_to_invoice: Dict[int, list[str]] = field(default_factory=dict)
    pos_total_amounts: Dict[int, Decimal] = field(default_factory=dict)
    invoice_pos_breakdown: Dict[str, Dict[int, Decimal]] = field(default_factory=dict)

    def register_owner(
        self, external_id: str, owner: OwnerProfile | SimpleNamespace
    ) -> None:
        self.owners_by_external[external_id] = owner

    def register_pet(self, external_id: str, pet: Pet | SimpleNamespace) -> None:
        self.pets_by_external[external_id] = pet

    def register_reservation(
        self, external_id: str, reservation: Reservation | SimpleNamespace
    ) -> None:
        self.reservations_by_external[external_id] = reservation

    def register_invoice(
        self, external_id: str, invoice: Invoice | SimpleNamespace
    ) -> None:
        self.invoices_by_external[external_id] = invoice

    @staticmethod
    def make_stub(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)


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


def load_reference_data(ctx: ImportContext) -> None:
    """Warm up lookup dictionaries used during import."""

    with ctx.mysql.cursor() as cur:
        cur.execute("SELECT id, name FROM species")
        ctx.species_map = {int(row["id"]): row["name"] for row in cur.fetchall()}

        cur.execute("SELECT id, name FROM breeds")
        ctx.breed_map = {int(row["id"]): row["name"] for row in cur.fetchall()}

        cur.execute("SELECT id, type FROM reservation_types WHERE is_deleted = 0")
        ctx.reservation_type_map = {
            int(row["id"]): row["type"] for row in cur.fetchall()
        }

        cur.execute("SELECT id, type FROM immunization_types")
        ctx.immunization_type_map = {
            int(row["id"]): row["type"] for row in cur.fetchall()
        }

        cur.execute("SELECT id, type FROM payment_methods WHERE status = 1")
        ctx.payment_method_map = {int(row["id"]): row["type"] for row in cur.fetchall()}

        cur.execute(
            "SELECT id, location_id, name, type_id, qty, price, hourly_credit, subscription_days, use_for_subscriptions, account_code_id "
            "FROM packages"
        )
        ctx.package_definitions = {int(row["id"]): row for row in cur.fetchall()}

        cur.execute(
            "SELECT id, owner_id, subtotal, discounts_total, tax_amount, total, payment_amount, create_stamp, location_id "
            "FROM pos_transactions"
        )
        ctx.pos_transaction_meta = {}
        for row in cur.fetchall():
            pos_id = int(row["id"])
            ctx.pos_transaction_meta[pos_id] = {
                "owner_id": row.get("owner_id"),
                "subtotal": to_decimal(row.get("subtotal")),
                "discounts_total": to_decimal(row.get("discounts_total")),
                "tax_total": to_decimal(row.get("tax_amount")),
                "total": to_decimal(row.get("total")),
                "payment_total": to_decimal(row.get("payment_amount")),
                "create_stamp": row.get("create_stamp"),
                "created_at": epoch_to_datetime(row.get("create_stamp")),
                "location_id": row.get("location_id"),
            }

        cur.execute(
            "SELECT id, pos_transaction_id, description, price, discounts_total, tax_amount "
            "FROM pos_transaction_items"
        )
        for row in cur.fetchall():
            pos_id = int(row["pos_transaction_id"])
            item_id = int(row["id"])
            normalized = {
                "id": item_id,
                "pos_transaction_id": pos_id,
                "description": row.get("description"),
                "price": to_decimal(row.get("price")),
                "discounts_total": to_decimal(row.get("discounts_total")),
                "tax_amount": to_decimal(row.get("tax_amount")),
            }
            ctx.pos_items_by_transaction.setdefault(pos_id, []).append(normalized)
            ctx.pos_item_details[item_id] = normalized

        cur.execute(
            "SELECT rs.reservation_id, pti.pos_transaction_id, pti.id AS pos_item_id "
            "FROM reservation_services rs "
            "JOIN pos_transaction_items pti ON rs.pos_transaction_item_id = pti.id"
        )
        for row in cur.fetchall():
            reservation_id = int(row["reservation_id"])
            pos_id = int(row["pos_transaction_id"])
            item_id = int(row["pos_item_id"])
            item = ctx.pos_item_details.get(item_id, {})
            ctx.pos_reservations.setdefault(pos_id, set()).add(reservation_id)
            ctx.reservation_items.setdefault(reservation_id, []).append(
                {
                    "reservation_id": reservation_id,
                    "pos_transaction_id": pos_id,
                    "item_id": item_id,
                    "description": item.get("description"),
                    "price": item.get("price", Decimal("0")),
                    "discounts_total": item.get("discounts_total", Decimal("0")),
                    "tax_amount": item.get("tax_amount", Decimal("0")),
                }
            )

        cur.execute(
            "SELECT payment_id, type, type_id, amount FROM payment_allocations WHERE active = 1"
        )
        for row in cur.fetchall():
            pid = int(row["payment_id"])
            ctx.payment_allocations.setdefault(pid, []).append(row)


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


def ensure_placeholder_owner(
    ctx: ImportContext,
    suffix: str,
    label: str,
) -> OwnerProfile | SimpleNamespace:
    external_id = f"gingr:owner:placeholder:{suffix}"
    existing = ctx.owners_by_external.get(external_id)
    if existing is not None:
        return existing

    if not ctx.dry_run:
        existing_db = ctx.session.execute(
            select(OwnerProfile).where(OwnerProfile.external_id == external_id)
        ).scalar_one_or_none()
        if existing_db:
            ctx.register_owner(external_id, existing_db)
            return existing_db

    placeholder_email = f"placeholder+{suffix}@eipr.local"
    if ctx.dry_run:
        stub = ctx.make_stub(
            id=external_id,
            external_id=external_id,
            user=ctx.make_stub(email=placeholder_email),
        )
        ctx.register_owner(external_id, stub)
        return stub

    user = User(
        account_id=ctx.account.id,
        email=placeholder_email,
        hashed_password=get_password_hash(secrets.token_urlsafe(16)),
        first_name="Archived",
        last_name=label,
        phone_number=None,
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
        is_primary_contact=True,
    )
    owner = OwnerProfile(
        user=user,
        external_id=external_id,
        email_opt_in=False,
        sms_opt_in=False,
        notes=f"Auto-created placeholder owner for {label}",
    )
    ctx.session.add(owner)
    ctx.session.flush()
    ctx.register_owner(external_id, owner)
    return owner


def ensure_placeholder_pet(
    ctx: ImportContext,
    owner_external: str,
    owner: OwnerProfile | SimpleNamespace,
) -> Pet | SimpleNamespace:
    placeholder_external = f"{owner_external}:pet:placeholder"
    existing = ctx.pets_by_external.get(placeholder_external)
    if existing:
        return existing

    if not ctx.dry_run:
        existing_db = ctx.session.execute(
            select(Pet).where(Pet.external_id == placeholder_external)
        ).scalar_one_or_none()
        if existing_db:
            ctx.register_pet(placeholder_external, existing_db)
            return existing_db

    if ctx.dry_run:
        stub = ctx.make_stub(
            id=placeholder_external,
            external_id=placeholder_external,
            owner_id=getattr(owner, "id", owner_external),
            name="Retail Pet",
        )
        ctx.register_pet(placeholder_external, stub)
        return stub

    pet = Pet(
        owner_id=getattr(owner, "id"),
        home_location_id=ctx.location.id,
        name="Retail Pet",
        pet_type=PetType.OTHER,
        notes="Auto-created for retail transactions",
        external_id=placeholder_external,
    )
    ctx.session.add(pet)
    ctx.session.flush()
    ctx.register_pet(placeholder_external, pet)
    return pet


def ensure_orphan_pet(
    ctx: ImportContext,
    pet_external: str,
) -> Pet | SimpleNamespace | None:
    existing = ctx.pets_by_external.get(pet_external)
    if existing is not None:
        return existing

    if not ctx.dry_run:
        existing_db = ctx.session.execute(
            select(Pet).where(Pet.external_id == pet_external)
        ).scalar_one_or_none()
        if existing_db:
            ctx.register_pet(pet_external, existing_db)
            return existing_db

    suffix = pet_external.replace(":", "-")
    owner = ensure_placeholder_owner(ctx, f"orphan-{suffix}", f"Orphan Pet {suffix}")

    if ctx.dry_run:
        stub = ctx.make_stub(
            id=pet_external,
            external_id=pet_external,
            owner_id=getattr(owner, "id", owner),
            name=f"Orphan Pet {suffix}",
        )
        ctx.register_pet(pet_external, stub)
        return stub

    pet = Pet(
        owner_id=getattr(owner, "id"),
        home_location_id=ctx.location.id,
        name=f"Orphan Pet {suffix}",
        pet_type=PetType.OTHER,
        notes="Auto-created placeholder pet for orphaned record",
        external_id=pet_external,
    )
    ctx.session.add(pet)
    ctx.session.flush()
    ctx.register_pet(pet_external, pet)
    return pet


def ensure_placeholder_reservation(
    ctx: ImportContext,
    reservation_external: str,
    pet: Pet | SimpleNamespace,
    start_at: dt.datetime,
) -> Reservation | SimpleNamespace:
    existing = ctx.reservations_by_external.get(reservation_external)
    if existing:
        return existing

    end_at = start_at + dt.timedelta(hours=1)

    if not ctx.dry_run:
        existing_db = ctx.session.execute(
            select(Reservation).where(Reservation.external_id == reservation_external)
        ).scalar_one_or_none()
        if existing_db:
            ctx.register_reservation(reservation_external, existing_db)
            return existing_db

    if ctx.dry_run:
        stub = ctx.make_stub(
            id=reservation_external,
            external_id=reservation_external,
            pet_id=getattr(pet, "id", pet),
            reservation_type=ReservationType.OTHER,
            status=ReservationStatus.CONFIRMED,
            start_at=start_at,
            end_at=end_at,
        )
        ctx.register_reservation(reservation_external, stub)
        return stub

    reservation = Reservation(
        account_id=ctx.account.id,
        location_id=ctx.location.id,
        pet_id=getattr(pet, "id"),
        reservation_type=ReservationType.OTHER,
        status=ReservationStatus.CONFIRMED,
        start_at=start_at,
        end_at=end_at,
        base_rate=Decimal("0"),
        notes="Placeholder reservation for retail transaction",
        external_id=reservation_external,
    )
    ctx.session.add(reservation)
    ctx.session.flush()
    ctx.register_reservation(reservation_external, reservation)
    return reservation


def reservation_external_to_invoice_external(reservation_external: str) -> str:
    prefix = "gingr:reservation:"
    if reservation_external.startswith(prefix):
        suffix = reservation_external[len(prefix) :]
        return f"gingr:invoice:{suffix}"
    return f"{reservation_external}:invoice"


def resolve_package_application(
    ctx: ImportContext, package_row: Dict[str, Any]
) -> PackageApplicationType:
    type_id = package_row.get("type_id")
    type_name = None
    if type_id is not None:
        try:
            type_name = ctx.reservation_type_map.get(int(type_id))
        except (ValueError, TypeError):
            type_name = None
    if type_name:
        lowered = type_name.lower()
        if "daycare" in lowered or "day care" in lowered:
            return PackageApplicationType.DAYCARE
        if "lodging" in lowered or "boarding" in lowered:
            return PackageApplicationType.BOARDING
        if "groom" in lowered or "spa" in lowered:
            return PackageApplicationType.GROOMING
        if "train" in lowered:
            return PackageApplicationType.GROOMING
    return PackageApplicationType.CURRENCY


def get_or_create_package_type(
    ctx: ImportContext, package_id: int
) -> PackageType | SimpleNamespace:
    existing = ctx.package_types_cache.get(package_id)
    if existing is not None:
        return existing

    package_row = ctx.package_definitions.get(package_id)
    name = package_row.get("name") if package_row else f"Package {package_id}"
    applies_to = resolve_package_application(ctx, package_row or {})
    credits = package_row.get("qty") if package_row else 1
    price = to_decimal(package_row.get("price")) if package_row else Decimal("0")

    if ctx.dry_run:
        stub = ctx.make_stub(
            id=f"gingr:package-type:{package_id}",
            name=name,
            applies_to=applies_to,
            credits_per_package=credits,
            price=price,
        )
        ctx.package_types_cache[package_id] = stub
        return stub

    package_type = ctx.session.execute(
        select(PackageType).where(
            PackageType.account_id == ctx.account.id,
            PackageType.name == name,
        )
    ).scalar_one_or_none()
    if package_type is None:
        package_type = PackageType(
            account_id=ctx.account.id,
            name=name,
            applies_to=applies_to,
            credits_per_package=int(credits or 1),
            price=price,
        )
        ctx.session.add(package_type)
        ctx.session.flush()
    ctx.package_types_cache[package_id] = package_type
    return package_type


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
    created_col = columns.get("created_at")
    updated_col = columns.get("updated_at")
    notes_col = columns.get("notes")

    if not table or not id_col:
        LOGGER.warning("Skipping owners import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                first_col,
                last_col,
                email_col,
                phone_col,
                created_col,
                updated_col,
                notes_col,
            ]
            if col
        }
    )
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        updated_col,
    ):
        raw_id = row.get(id_col)
        if raw_id is None:
            stats.reject("owner missing id")
            continue
        external_id = f"gingr:owner:{raw_id}"
        existing = ctx.session.execute(
            select(OwnerProfile).where(OwnerProfile.external_id == external_id)
        ).scalar_one_or_none()
        if existing:
            stats.skip()
            ctx.register_owner(external_id, existing)
            continue

        first_name = (
            (row.get(first_col) or "Customer").strip() if first_col else "Customer"
        )
        last_name = (
            (row.get(last_col) or str(raw_id)).strip() if last_col else str(raw_id)
        )
        email = normalize_email(row.get(email_col) if email_col else None)
        phone = normalize_phone(row.get(phone_col) if phone_col else None)
        owner_notes = row.get(notes_col) if notes_col else None
        if owner_notes is not None:
            owner_notes = str(owner_notes)
            if len(owner_notes) > 1024:
                owner_notes = owner_notes[:1024]

        if email:
            existing_user = ctx.session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            if existing_user:
                unique_suffix = secrets.token_hex(4)
                local, domain = existing_user.email.split("@", 1)
                email = f"{local}+{unique_suffix}@{domain}"

        if ctx.dry_run:
            stub = ctx.make_stub(
                id=external_id,
                external_id=external_id,
                email=email or f"imported+{raw_id}@example.com",
                phone_number=phone,
            )
            ctx.register_owner(external_id, stub)
            stats.create()
            continue

        password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            account_id=ctx.account.id,
            email=email or f"imported+{external_id.replace(':', '')}@example.com",
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
            notes=owner_notes,
        )
        ctx.session.add(owner)
        ctx.session.flush()
        ctx.register_owner(external_id, owner)
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
    species_col = columns.get("species_id")
    breed_col = columns.get("breed_id")
    gender_col = columns.get("gender")
    dob_col = columns.get("dob")
    notes_col = columns.get("notes")
    created_col = columns.get("created_at")

    if not table or not id_col or not owner_col or not name_col:
        LOGGER.warning("Skipping pets import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                owner_col,
                name_col,
                species_col,
                breed_col,
                gender_col,
                dob_col,
                notes_col,
                created_col,
            ]
            if col
        }
    )
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        created_col,
    ):
        raw_id = row.get(id_col)
        owner_raw = row.get(owner_col)
        if raw_id is None or owner_raw is None:
            stats.reject("pet missing id or owner id")
            continue
        external_id = f"gingr:pet:{raw_id}"
        owner_external = f"gingr:owner:{owner_raw}"

        owner = ctx.owners_by_external.get(owner_external)
        if owner is None and not ctx.dry_run:
            owner = ctx.session.execute(
                select(OwnerProfile).where(OwnerProfile.external_id == owner_external)
            ).scalar_one_or_none()
            if owner:
                ctx.register_owner(owner_external, owner)
        if owner is None:
            stats.reject(f"owner {owner_external} not found for pet {external_id}")
            continue

        existing = ctx.session.execute(
            select(Pet).where(Pet.external_id == external_id)
        ).scalar_one_or_none()
        if existing:
            stats.skip()
            ctx.register_pet(external_id, existing)
            continue

        species_name = None
        if species_col:
            species_key = safe_int(row.get(species_col))
            if species_key is not None:
                species_name = ctx.species_map.get(species_key)
        pet_type = pet_type_from_string(species_name)

        breed_name = None
        if breed_col:
            breed_key = safe_int(row.get(breed_col))
            if breed_key is not None:
                breed_name = ctx.breed_map.get(breed_key)

        gender = (row.get(gender_col) or "").strip() if gender_col else ""
        source_notes = row.get(notes_col) if notes_col else None
        combined_notes = source_notes
        if gender:
            gender_note = f"Gender: {gender}"
            combined_notes = (
                f"{source_notes}\n{gender_note}" if source_notes else gender_note
            )
        if combined_notes is not None:
            combined_notes = str(combined_notes)
            if len(combined_notes) > 1024:
                combined_notes = combined_notes[:1024]

        if ctx.dry_run:
            stub = ctx.make_stub(
                id=external_id,
                external_id=external_id,
                owner_id=getattr(owner, "id", owner_external),
            )
            ctx.register_pet(external_id, stub)
            stats.create()
            continue

        pet = Pet(
            owner_id=getattr(owner, "id"),
            home_location_id=ctx.location.id,
            name=(row.get(name_col) or "Pet").strip(),
            pet_type=pet_type,
            breed=breed_name,
            notes=combined_notes,
            date_of_birth=epoch_to_date(row.get(dob_col) if dob_col else None),
            external_id=external_id,
        )
        ctx.session.add(pet)
        ctx.session.flush()
        ctx.register_pet(external_id, pet)
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
    type_col = columns.get("type_id")
    expires_col = columns.get("expires_on")
    updated_col = columns.get("updated_at")
    notes_col = columns.get("notes")

    if not table or not id_col or not pet_col or not type_col:
        LOGGER.warning("Skipping immunizations import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                pet_col,
                type_col,
                expires_col,
                updated_col,
                notes_col,
            ]
            if col
        }
    )
    for row in fetch_rows(ctx.mysql, table, select_columns, ctx.limit, None, None):
        raw_id = row.get(id_col)
        pet_raw = row.get(pet_col)
        if raw_id is None or pet_raw is None:
            stats.reject("immunization missing id or pet id")
            continue
        pet_external = f"gingr:pet:{pet_raw}"

        pet = ctx.pets_by_external.get(pet_external)
        if pet is None and not ctx.dry_run:
            pet = ctx.session.execute(
                select(Pet).where(Pet.external_id == pet_external)
            ).scalar_one_or_none()
            if pet:
                ctx.register_pet(pet_external, pet)
        if not pet:
            pet = ensure_orphan_pet(ctx, pet_external)
        if not pet:
            stats.reject(f"pet {pet_external} missing for immunization {raw_id}")
            continue

        type_raw = row.get(type_col)
        type_name = None
        if type_raw is not None:
            try:
                type_name = ctx.immunization_type_map.get(int(type_raw))
            except (ValueError, TypeError):
                type_name = None
        if not type_name:
            type_name = f"Gingr Type {type_raw}" if type_raw is not None else "General"

        issued_on = epoch_to_date(row.get(updated_col)) or dt.date.today()
        expires_on = epoch_to_date(row.get(expires_col))
        notes = row.get(notes_col) if notes_col else None

        status = ImmunizationStatus.PENDING
        today = dt.date.today()
        if expires_on:
            if expires_on < today:
                status = ImmunizationStatus.EXPIRED
            elif (expires_on - today).days <= 30:
                status = ImmunizationStatus.EXPIRING
            else:
                status = ImmunizationStatus.CURRENT

        if ctx.dry_run:
            ctx.make_stub(
                pet_id=getattr(pet, "id", pet_external),
                type_name=type_name,
            )
            stats.create()
            continue

        type_obj = ensure_immunization_type(ctx.session, ctx.account.id, type_name)

        query = select(ImmunizationRecord).where(
            ImmunizationRecord.pet_id == getattr(pet, "id"),
            ImmunizationRecord.type_id == type_obj.id,
            ImmunizationRecord.issued_on == issued_on,
        )
        if expires_on is None:
            query = query.where(ImmunizationRecord.expires_on.is_(None))
        else:
            query = query.where(ImmunizationRecord.expires_on == expires_on)
        existing = ctx.session.execute(query).scalar_one_or_none()
        if existing:
            stats.skip()
            continue

        record = ImmunizationRecord(
            account_id=ctx.account.id,
            pet_id=getattr(pet, "id"),
            type_id=type_obj.id,
            issued_on=issued_on,
            expires_on=expires_on,
            status=status,
            notes=notes or f"Imported from Gingr ID {raw_id}",
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
    type_col = columns.get("type_id")
    location_col = columns.get("location_id")
    notes_col = columns.get("notes")
    check_in_col = columns.get("check_in_at")
    check_out_col = columns.get("check_out_at")
    cancel_col = columns.get("cancel_at")
    confirmed_col = columns.get("confirmed_at")
    waitlist_col = columns.get("waitlist_at")
    waitlist_accept_col = columns.get("waitlist_accept_at")
    base_rate_col = columns.get("base_rate")
    final_rate_col = columns.get("final_rate")
    cancel_total_col = columns.get("cancel_total")
    created_col = columns.get("created_at")

    if not table or not id_col or not pet_col or not start_col or not end_col:
        LOGGER.warning("Skipping reservations import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                pet_col,
                start_col,
                end_col,
                type_col,
                location_col,
                notes_col,
                check_in_col,
                check_out_col,
                cancel_col,
                confirmed_col,
                waitlist_col,
                waitlist_accept_col,
                base_rate_col,
                final_rate_col,
                cancel_total_col,
                created_col,
            ]
            if col
        }
    )
    for row in fetch_rows(
        ctx.mysql,
        table,
        select_columns,
        ctx.limit,
        ctx.since,
        created_col,
    ):
        raw_id = row.get(id_col)
        pet_raw = row.get(pet_col)
        if raw_id is None or pet_raw is None:
            stats.reject("reservation missing id or pet id")
            continue
        external_id = f"gingr:reservation:{raw_id}"
        pet_external = f"gingr:pet:{pet_raw}"

        pet = ctx.pets_by_external.get(pet_external)
        if pet is None and not ctx.dry_run:
            pet = ctx.session.execute(
                select(Pet).where(Pet.external_id == pet_external)
            ).scalar_one_or_none()
            if pet:
                ctx.register_pet(pet_external, pet)
        if not pet:
            pet = ensure_orphan_pet(ctx, pet_external)
        if not pet:
            stats.reject(f"pet {pet_external} missing for reservation {external_id}")
            continue

        existing = ctx.session.execute(
            select(Reservation).where(Reservation.external_id == external_id)
        ).scalar_one_or_none()
        if existing:
            stats.skip()
            ctx.register_reservation(external_id, existing)
            continue

        start_at = epoch_to_datetime(row.get(start_col)) or dt.datetime.now(
            dt.timezone.utc
        )
        end_at = epoch_to_datetime(row.get(end_col)) or start_at
        if end_at < start_at:
            end_at = start_at + dt.timedelta(hours=1)

        check_in_at = epoch_to_datetime(row.get(check_in_col)) if check_in_col else None
        check_out_at = (
            epoch_to_datetime(row.get(check_out_col)) if check_out_col else None
        )
        cancel_at = epoch_to_datetime(row.get(cancel_col)) if cancel_col else None
        confirmed_at = (
            epoch_to_datetime(row.get(confirmed_col)) if confirmed_col else None
        )
        waitlist_at = epoch_to_datetime(row.get(waitlist_col)) if waitlist_col else None
        waitlist_accept_at = (
            epoch_to_datetime(row.get(waitlist_accept_col))
            if waitlist_accept_col
            else None
        )

        type_name = None
        if type_col:
            type_key = safe_int(row.get(type_col))
            if type_key is not None:
                type_name = ctx.reservation_type_map.get(type_key)
        res_type = reservation_type_from_string(type_name)

        if cancel_at:
            status = ReservationStatus.CANCELED
        elif check_out_at:
            status = ReservationStatus.CHECKED_OUT
        elif check_in_at:
            status = ReservationStatus.CHECKED_IN
        elif waitlist_accept_at:
            status = ReservationStatus.OFFERED_FROM_WAITLIST
        elif waitlist_at:
            status = ReservationStatus.PENDING_CONFIRMATION
        elif confirmed_at:
            status = ReservationStatus.CONFIRMED
        else:
            status = ReservationStatus.CONFIRMED

        base_rate = (
            to_decimal(row.get(base_rate_col)) if base_rate_col else Decimal("0")
        )
        final_rate = (
            to_decimal(row.get(final_rate_col)) if final_rate_col else Decimal("0")
        )
        monetary_total = final_rate if final_rate else base_rate
        notes = row.get(notes_col) if notes_col else None

        if ctx.dry_run:
            stub = ctx.make_stub(
                id=external_id,
                external_id=external_id,
                pet_id=getattr(pet, "id", pet_external),
                reservation_type=res_type,
                status=status,
                start_at=start_at,
                end_at=end_at,
            )
            ctx.register_reservation(external_id, stub)
            stats.create()
            continue

        reservation = Reservation(
            account_id=ctx.account.id,
            location_id=ctx.location.id,
            pet_id=getattr(pet, "id"),
            reservation_type=res_type,
            status=status,
            start_at=start_at,
            end_at=end_at,
            base_rate=monetary_total,
            notes=notes,
            check_in_at=check_in_at,
            check_out_at=check_out_at,
            external_id=external_id,
        )
        ctx.session.add(reservation)
        ctx.session.flush()
        ctx.register_reservation(external_id, reservation)
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
    ctx.pos_to_invoice.clear()
    ctx.invoice_payment_totals.clear()

    reservation_financials: Dict[int, Dict[str, Any]] = {}
    pos_totals: Dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    for reservation_id, items in ctx.reservation_items.items():
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")
        pos_breakdown: Dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

        for item in items:
            price = item.get("price", Decimal("0"))
            discount = item.get("discounts_total", Decimal("0"))
            tax = item.get("tax_amount", Decimal("0"))
            line_total = price - discount + tax
            subtotal += price
            discount_total += discount
            tax_total += tax
            pos_id = item.get("pos_transaction_id")
            if pos_id is not None:
                pos_breakdown[int(pos_id)] += line_total

        total = subtotal - discount_total + tax_total
        reservation_financials[int(reservation_id)] = {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "tax_total": tax_total,
            "total": total,
            "pos_breakdown": pos_breakdown,
        }

        for pos_id, amount in pos_breakdown.items():
            pos_totals[int(pos_id)] += amount

    def get_reservation_obj(
        reservation_external: str,
    ) -> Reservation | SimpleNamespace | None:
        reservation = ctx.reservations_by_external.get(reservation_external)
        if reservation is None and not ctx.dry_run:
            reservation = ctx.session.execute(
                select(Reservation).where(
                    Reservation.external_id == reservation_external
                )
            ).scalar_one_or_none()
            if reservation:
                ctx.register_reservation(reservation_external, reservation)
        return reservation

    def create_invoice(
        reservation_external: str,
        reservation_obj: Reservation | SimpleNamespace,
        financials: Dict[str, Any],
        created_at: Optional[dt.datetime],
        pos_breakdown: Dict[int, Decimal],
    ) -> None:
        invoice_external = reservation_external_to_invoice_external(
            reservation_external
        )

        existing_invoice = ctx.invoices_by_external.get(invoice_external)
        if existing_invoice is None and not ctx.dry_run:
            existing_invoice = ctx.session.execute(
                select(Invoice).where(Invoice.external_id == invoice_external)
            ).scalar_one_or_none()
            if existing_invoice:
                ctx.register_invoice(invoice_external, existing_invoice)

        subtotal = financials.get("subtotal", Decimal("0"))
        discount_total = financials.get("discount_total", Decimal("0"))
        tax_total = financials.get("tax_total", Decimal("0"))
        total = financials.get("total", Decimal("0"))

        for pos_id in pos_breakdown.keys():
            ctx.pos_to_invoice.setdefault(int(pos_id), []).append(invoice_external)
        ctx.invoice_pos_breakdown[invoice_external] = {
            int(pos_id): amount for pos_id, amount in pos_breakdown.items()
        }

        if existing_invoice is not None:
            stats.skip()
            if not ctx.dry_run:
                ctx.invoice_payment_totals.setdefault(invoice_external, Decimal("0"))
            else:
                ctx.invoice_payment_totals[invoice_external] = Decimal("0")
            return

        if ctx.dry_run:
            stub = ctx.make_stub(
                id=invoice_external,
                external_id=invoice_external,
                reservation_id=getattr(reservation_obj, "id", reservation_external),
                subtotal=subtotal,
                discount_total=discount_total,
                tax_total=tax_total,
                total=total,
                status=InvoiceStatus.PENDING,
            )
            ctx.register_invoice(invoice_external, stub)
            ctx.invoice_payment_totals[invoice_external] = Decimal("0")
            stats.create()
            return

        invoice = Invoice(
            account_id=ctx.account.id,
            reservation_id=getattr(reservation_obj, "id"),
            status=InvoiceStatus.PENDING,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            credits_total=Decimal("0"),
            total=total,
            total_amount=total,
            paid_at=None,
            external_id=invoice_external,
        )
        if created_at:
            invoice.created_at = created_at
        ctx.session.add(invoice)
        ctx.session.flush()
        ctx.register_invoice(invoice_external, invoice)
        ctx.invoice_payment_totals[invoice_external] = Decimal("0")
        stats.create()

    # Create invoices for reservations with financial data
    for reservation_id, fin in reservation_financials.items():
        reservation_external = f"gingr:reservation:{reservation_id}"
        reservation_obj = get_reservation_obj(reservation_external)
        if reservation_obj is None:
            stats.reject(f"reservation {reservation_external} missing for invoice")
            continue

        pos_ids = fin.get("pos_breakdown", {})
        created_at_candidates: list[dt.datetime] = []
        for pos_id in pos_ids.keys():
            candidate = ctx.pos_transaction_meta.get(pos_id, {}).get("created_at")
            if isinstance(candidate, dt.datetime):
                created_at_candidates.append(candidate)
        created_at = min(created_at_candidates) if created_at_candidates else None

        create_invoice(
            reservation_external,
            reservation_obj,
            fin,
            created_at,
            fin.get("pos_breakdown", {}),
        )

    handled_reservations = {
        f"gingr:reservation:{reservation_id}"
        for reservation_id in reservation_financials
    }

    # Create zero-amount invoices for any remaining reservations
    for reservation_external, reservation_obj in ctx.reservations_by_external.items():
        if reservation_external in handled_reservations:
            continue
        if not reservation_external.startswith("gingr:reservation:"):
            continue

        fin = {
            "subtotal": getattr(reservation_obj, "base_rate", Decimal("0")),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "total": getattr(reservation_obj, "base_rate", Decimal("0")),
        }
        create_invoice(reservation_external, reservation_obj, fin, None, {})

    # Handle standalone POS transactions (retail, etc.)
    for pos_id, meta in ctx.pos_transaction_meta.items():
        if pos_id in ctx.pos_reservations:
            continue
        owner_raw = meta.get("owner_id")
        owner: OwnerProfile | SimpleNamespace | None
        owner_external: str
        if owner_raw in (None, "", 0, "0"):
            owner = ensure_placeholder_owner(ctx, f"pos-{pos_id}", f"POS {pos_id}")
            owner_external = getattr(
                owner, "external_id", f"gingr:owner:placeholder:pos-{pos_id}"
            )
            ctx.register_owner(owner_external, owner)
        else:
            owner_external = f"gingr:owner:{owner_raw}"
            owner = ctx.owners_by_external.get(owner_external)
            if owner is None and not ctx.dry_run:
                owner = ctx.session.execute(
                    select(OwnerProfile).where(
                        OwnerProfile.external_id == owner_external
                    )
                ).scalar_one_or_none()
                if owner:
                    ctx.register_owner(owner_external, owner)
            if owner is None:
                owner = ensure_placeholder_owner(
                    ctx,
                    f"missing-owner-{owner_raw}",
                    f"Missing Owner {owner_raw}",
                )
                ctx.register_owner(owner_external, owner)

        pet = ensure_placeholder_pet(ctx, owner_external, owner)
        created_at = meta.get("created_at") or dt.datetime.now(dt.timezone.utc)
        reservation_external = f"gingr:reservation:pos:{pos_id}"
        reservation_obj = ensure_placeholder_reservation(
            ctx, reservation_external, pet, created_at
        )

        fin = {
            "subtotal": meta.get("subtotal", Decimal("0")),
            "discount_total": meta.get("discounts_total", Decimal("0")),
            "tax_total": meta.get("tax_total", Decimal("0")),
            "total": meta.get("total", Decimal("0")),
        }
        total_amount = fin["total"] or Decimal("0")
        create_invoice(
            reservation_external,
            reservation_obj,
            fin,
            created_at,
            {pos_id: total_amount},
        )
        pos_totals[pos_id] += total_amount

    if not ctx.dry_run:
        ctx.session.commit()
    ctx.pos_total_amounts = dict(pos_totals)
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
    amount_col = columns.get("amount")
    owner_col = columns.get("owner_id")
    status_flag_col = columns.get("status_flag")
    method_col = columns.get("payment_method_id")
    processed_col = columns.get("created_at")
    description_col = columns.get("description")
    processor_col = columns.get("processor_ref")
    external_ref_col = columns.get("external_ref")
    refund_ref_col = columns.get("refund_ref")

    if not table or not id_col or not amount_col:
        LOGGER.warning("Skipping payments import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                owner_col,
                amount_col,
                status_flag_col,
                method_col,
                processed_col,
                description_col,
                processor_col,
                external_ref_col,
                refund_ref_col,
            ]
            if col
        }
    )

    invoice_paid_dates: Dict[str, dt.datetime] = {}

    for row in fetch_rows(ctx.mysql, table, select_columns, ctx.limit, None, None):
        payment_id_raw = row.get(id_col)
        if payment_id_raw is None:
            stats.reject("payment missing id")
            continue
        payment_id = int(payment_id_raw)
        external_id_root = f"gingr:payment:{payment_id}"

        amount_total = to_decimal(row.get(amount_col))
        processed_at = (
            epoch_to_datetime(row.get(processed_col)) if processed_col else None
        )
        status_flag = row.get(status_flag_col)
        refund_reference = row.get(refund_ref_col)
        method_key = safe_int(row.get(method_col))
        method_name = (
            ctx.payment_method_map.get(method_key) if method_key is not None else None
        )
        provider = (method_name or "gingr").lower()[:32]
        description = row.get(description_col)
        processor_ref = row.get(processor_col)
        external_ref = row.get(external_ref_col)

        allocation_rows = ctx.payment_allocations.get(payment_id, [])
        invoice_allocations: list[tuple[str, Decimal]] = []

        for alloc in allocation_rows:
            alloc_amount = (
                to_decimal(alloc.get("amount"))
                if alloc.get("amount") is not None
                else amount_total
            )
            alloc_type = safe_int(alloc.get("type")) or 1
            target_id = alloc.get("type_id")
            if target_id is None:
                continue

            if alloc_type == 2:
                reservation_external = f"gingr:reservation:{target_id}"
                invoice_external = reservation_external_to_invoice_external(
                    reservation_external
                )
                invoice_allocations.append((invoice_external, alloc_amount))
                continue

            try:
                pos_id = int(target_id)
            except (ValueError, TypeError):
                continue

            invoices = ctx.pos_to_invoice.get(pos_id, [])
            if not invoices:
                continue
            total_for_pos = ctx.pos_total_amounts.get(pos_id, Decimal("0"))
            if total_for_pos <= Decimal("0"):
                share = alloc_amount / len(invoices)
                for invoice_external in invoices:
                    invoice_allocations.append((invoice_external, share))
                continue
            for invoice_external in invoices:
                share_total = ctx.invoice_pos_breakdown.get(invoice_external, {}).get(
                    pos_id, Decimal("0")
                )
                if share_total <= Decimal("0"):
                    continue
                proportional_amount = alloc_amount * (share_total / total_for_pos)
                invoice_allocations.append((invoice_external, proportional_amount))

        if not invoice_allocations:
            stats.reject(f"payment {payment_id} has no invoice allocations")
            continue

        if refund_reference:
            payment_status = PaymentTransactionStatus.REFUNDED
        elif amount_total <= Decimal("0"):
            payment_status = PaymentTransactionStatus.CANCELED
        elif status_flag in (1, "1", True, "captured"):
            payment_status = PaymentTransactionStatus.SUCCEEDED
        else:
            payment_status = PaymentTransactionStatus.PROCESSING

        owner_external = None
        owner_raw = row.get(owner_col)
        if owner_raw is not None:
            owner_external = f"gingr:owner:{owner_raw}"

        for invoice_external, partial_amount in invoice_allocations:
            invoice_obj = ctx.invoices_by_external.get(invoice_external)
            if invoice_obj is None and not ctx.dry_run:
                invoice_obj = ctx.session.execute(
                    select(Invoice).where(Invoice.external_id == invoice_external)
                ).scalar_one_or_none()
                if invoice_obj:
                    ctx.register_invoice(invoice_external, invoice_obj)
            if invoice_obj is None:
                stats.reject(
                    f"invoice {invoice_external} missing for payment {payment_id}"
                )
                continue

            payment_external_id = f"{external_id_root}:{invoice_external}"

            if ctx.dry_run:
                ctx.invoice_payment_totals[invoice_external] = (
                    ctx.invoice_payment_totals.get(invoice_external, Decimal("0"))
                    + partial_amount
                )
                stats.create()
                continue

            existing_payment = ctx.session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.external_id == payment_external_id
                )
            ).scalar_one_or_none()
            if existing_payment:
                stats.skip()
                continue

            owner_id = None
            if owner_external:
                owner_obj = ctx.owners_by_external.get(owner_external)
                if owner_obj is None:
                    owner_obj = invoice_obj.reservation.pet.owner
                    ctx.register_owner(owner_external, owner_obj)
                owner_id = getattr(owner_obj, "id", None)
            if owner_id is None:
                owner_id = invoice_obj.reservation.pet.owner_id

            intent_id = None
            for candidate in (processor_ref, external_ref):
                if candidate is None:
                    continue
                candidate_str = str(candidate).strip()
                if candidate_str and candidate_str != "0":
                    intent_id = candidate_str
                    break

            payment = PaymentTransaction(
                account_id=ctx.account.id,
                invoice_id=invoice_obj.id,
                owner_id=owner_id,
                provider=provider,
                provider_payment_intent_id=intent_id,
                amount=partial_amount,
                status=payment_status,
                external_id=payment_external_id,
                failure_reason=(
                    description
                    if payment_status != PaymentTransactionStatus.SUCCEEDED
                    else None
                ),
            )
            if processed_at:
                payment.created_at = processed_at
            ctx.session.add(payment)

            ctx.invoice_payment_totals[invoice_external] = (
                ctx.invoice_payment_totals.get(invoice_external, Decimal("0"))
                + partial_amount
            )
            if processed_at:
                current_paid_at = invoice_paid_dates.get(invoice_external)
                if current_paid_at is None or processed_at < current_paid_at:
                    invoice_paid_dates[invoice_external] = processed_at
            stats.create()

    if not ctx.dry_run:
        for invoice_external, invoice_obj in ctx.invoices_by_external.items():
            if not isinstance(invoice_obj, Invoice):
                continue
            paid_amount = ctx.invoice_payment_totals.get(invoice_external, Decimal("0"))
            if paid_amount >= invoice_obj.total - Decimal("0.01"):
                invoice_obj.status = InvoiceStatus.PAID
                if invoice_external in invoice_paid_dates:
                    invoice_obj.paid_at = invoice_paid_dates[invoice_external]
            else:
                invoice_obj.status = InvoiceStatus.PENDING
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
    package_col = columns.get("package_id")
    credits_col = columns.get("credits_remaining")
    expires_col = columns.get("expires_at")
    pos_col = columns.get("pos_transaction_id")
    value_col = columns.get("value_per_credit")

    if not table or not id_col or not owner_col or not credits_col or not package_col:
        LOGGER.warning("Skipping packages import: mapping incomplete")
        return stats

    select_columns = sorted(
        {
            col
            for col in [
                id_col,
                owner_col,
                package_col,
                credits_col,
                expires_col,
                pos_col,
                value_col,
            ]
            if col
        }
    )
    for row in fetch_rows(ctx.mysql, table, select_columns, ctx.limit, None, None):
        raw_id = row.get(id_col)
        owner_raw = row.get(owner_col)
        package_raw = row.get(package_col)
        if raw_id is None or owner_raw is None or package_raw is None:
            stats.reject("package credit missing id, owner id, or package id")
            continue
        external_id = f"gingr:package-credit:{raw_id}"
        owner_external = f"gingr:owner:{owner_raw}"

        owner = ctx.owners_by_external.get(owner_external)
        if owner is None and not ctx.dry_run:
            owner = ctx.session.execute(
                select(OwnerProfile).where(OwnerProfile.external_id == owner_external)
            ).scalar_one_or_none()
            if owner:
                ctx.register_owner(owner_external, owner)
        if owner is None:
            stats.reject(f"owner {owner_external} missing for package credit {raw_id}")
            continue

        if not ctx.dry_run:
            existing = ctx.session.execute(
                select(PackageCredit).where(PackageCredit.external_id == external_id)
            ).scalar_one_or_none()
            if existing:
                stats.skip()
                continue

        package_id = safe_int(package_raw)
        if package_id is None:
            stats.reject(f"invalid package id for credit {raw_id}")
            continue

        package_type = get_or_create_package_type(ctx, package_id)

        credits_value = row.get(credits_col)
        credits = safe_int(credits_value) or 0

        expires_at = epoch_to_datetime(row.get(expires_col)) if expires_col else None
        note = None
        if value_col and row.get(value_col) is not None:
            note = f"Value per credit: {row.get(value_col)}"

        invoice_id = None
        pos_raw = row.get(pos_col)
        if pos_raw is not None:
            pos_id = safe_int(pos_raw)
            if pos_id is not None:
                invoice_externals = ctx.pos_to_invoice.get(pos_id, [])
                if invoice_externals:
                    invoice_external = invoice_externals[0]
                    invoice_obj = ctx.invoices_by_external.get(invoice_external)
                    if invoice_obj is None and not ctx.dry_run:
                        invoice_obj = ctx.session.execute(
                            select(Invoice).where(
                                Invoice.external_id == invoice_external
                            )
                        ).scalar_one_or_none()
                        if invoice_obj:
                            ctx.register_invoice(invoice_external, invoice_obj)
                    if invoice_obj is not None:
                        invoice_id = getattr(invoice_obj, "id", None)

        source = (
            PackageCreditSource.PURCHASE
            if invoice_id is not None
            else PackageCreditSource.ADJUST
        )

        if ctx.dry_run:
            stats.create()
            continue

        package_credit = PackageCredit(
            account_id=ctx.account.id,
            owner_id=getattr(owner, "id"),
            package_type_id=getattr(package_type, "id", None),
            credits=credits,
            source=source,
            invoice_id=invoice_id,
            reservation_id=None,
            note=note,
            external_id=external_id,
        )
        if expires_at:
            package_credit.created_at = expires_at
        ctx.session.add(package_credit)
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

    sync_url = resolve_sync_database_url()
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

    load_reference_data(ctx)

    stats_list = run_import(ctx)

    mysql.close()
    if not dry_run:
        session.commit()
    session.close()

    total_processed = sum(stat.processed for stat in stats_list)
    total_rejected = sum(len(stat.rejects) for stat in stats_list)
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
