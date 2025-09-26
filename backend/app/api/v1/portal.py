"""Customer portal helper endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.core.config import get_settings
from app.integrations import StripeClient, StripeClientError
from app.models import (
    Account,
    ImmunizationRecord,
    Invoice,
    InvoiceStatus,
    Location,
    OwnerIcon,
    OwnerProfile,
    Pet,
    Reservation,
    ReservationStatus,
    ReservationType,
    User,
    UserRole,
)
from app.schemas.document import DocumentCreate, DocumentRead
from app.schemas.invoice import InvoiceRead
from app.schemas.owner import OwnerRead
from app.schemas.pet import PetRead
from app.schemas.reservation import ReservationRead
from app.services import (
    billing_service,
    document_service,
    owner_service,
    reservation_service,
)
from app.services.auth_service import authenticate_user, create_access_token_for_user

router = APIRouter(prefix="/portal", tags=["portal"])


def _optional_stripe_client() -> StripeClient | None:
    try:
        return deps.get_stripe_client()
    except HTTPException:
        return None


_SETTINGS_CACHE = get_settings
_PRESIGNED_UPLOADS: dict[str, dict[str, str]] = {}


class PortalLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PortalLoginResponse(BaseModel):
    access_token: str


class PortalRegisterOwnerRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: str | None = None
    account_slug: str | None = None


class PortalRegisterOwnerResponse(BaseModel):
    owner: OwnerRead
    access_token: str


class PortalReservationRequest(BaseModel):
    pet_id: uuid.UUID
    reservation_type: ReservationType
    start_at: datetime = Field(description="ISO8601 start timestamp")
    end_at: datetime = Field(description="ISO8601 end timestamp")
    notes: str | None = None
    location_id: uuid.UUID | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pet_id": str(uuid.uuid4()),
                    "reservation_type": "boarding",
                    "start_at": "2025-01-01T08:00:00Z",
                    "end_at": "2025-01-03T08:00:00Z",
                    "notes": "Rex prefers the large kennel",
                }
            ]
        }
    }


class PortalMeResponse(BaseModel):
    owner: OwnerRead
    pets: list[PetRead]
    upcoming_reservations: list[ReservationRead]
    past_reservations: list[ReservationRead]
    unpaid_invoices: list[InvoiceRead]
    recent_paid_invoices: list[InvoiceRead]


class PortalInvoicesResponse(BaseModel):
    unpaid: list[InvoiceRead]
    recent_paid: list[InvoiceRead]


class PortalPaymentIntentRequest(BaseModel):
    invoice_id: uuid.UUID


class PortalPaymentIntentResponse(BaseModel):
    client_secret: str
    transaction_id: str
    invoice_id: uuid.UUID


class PortalDocumentPresignRequest(BaseModel):
    filename: str
    content_type: str
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None


class PortalDocumentPresignResponse(BaseModel):
    upload_ref: str
    upload_url: str
    headers: dict[str, str]


class PortalDocumentFinalizeRequest(BaseModel):
    upload_ref: str
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None


class PortalDocumentFinalizeResponse(BaseModel):
    document: DocumentRead


async def _resolve_account(
    session: AsyncSession,
    *,
    explicit_slug: str | None = None,
) -> Account:
    settings = _SETTINGS_CACHE()
    slug = explicit_slug or settings.portal_account_slug
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Portal registration is not configured",
        )
    slug = slug.lower()
    result = await session.execute(select(Account).where(Account.slug == slug))
    account = result.scalar_one_or_none()
    if account is None:
        fallback = await session.execute(
            select(Account).order_by(Account.created_at.asc()).limit(1)
        )
        account = fallback.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


async def _ensure_portal_owner(
    session: AsyncSession,
    current_user: User,
) -> OwnerProfile:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access is restricted to pet parents",
        )
    owner = await owner_service.get_owner_by_user(session, user_id=current_user.id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner profile not found"
        )
    stmt = (
        select(OwnerProfile)
        .options(
            selectinload(OwnerProfile.user),
            selectinload(OwnerProfile.icon_assignments).selectinload(OwnerIcon.icon),
        )
        .where(OwnerProfile.id == owner.id)
    )
    result = await session.execute(stmt)
    hydrated = result.scalar_one_or_none()
    if hydrated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner profile not found"
        )
    return hydrated


async def _load_owner_pets(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[Pet]:
    stmt: Select[tuple[Pet]] = (
        select(Pet)
        .where(Pet.owner_id == owner_id)
        .options(
            selectinload(Pet.owner).selectinload(OwnerProfile.user),
            selectinload(Pet.immunization_records).selectinload(
                ImmunizationRecord.immunization_type
            ),
            selectinload(Pet.icon_assignments),
        )
        .order_by(Pet.created_at.asc())
    )
    result = await session.execute(stmt)
    pets = list(result.scalars().unique().all())
    # Ensure pets belong to the account
    filtered: list[Pet] = []
    for pet in pets:
        if pet.owner.user.account_id == account_id:  # type: ignore[union-attr]
            filtered.append(pet)
    return filtered


async def _load_owner_reservations(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[Reservation]:
    stmt: Select[tuple[Reservation]] = (
        select(Reservation)
        .join(Pet, Reservation.pet_id == Pet.id)
        .where(Reservation.account_id == account_id, Pet.owner_id == owner_id)
        .options(
            selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Reservation.location),
            selectinload(Reservation.invoice).selectinload(Invoice.items),
            selectinload(Reservation.feeding_schedules),
            selectinload(Reservation.medication_schedules),
        )
        .order_by(Reservation.start_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _categorise_reservations(
    reservations: Sequence[Reservation],
) -> tuple[list[Reservation], list[Reservation]]:
    now = datetime.now(UTC)
    upcoming: list[Reservation] = []
    past: list[Reservation] = []
    for reservation in reservations:
        if reservation.status in {
            ReservationStatus.REQUESTED,
            ReservationStatus.ACCEPTED,
            ReservationStatus.CONFIRMED,
            ReservationStatus.CHECKED_IN,
        }:
            upcoming.append(reservation)
            continue
        end_at = _ensure_utc(reservation.end_at) if reservation.end_at else None
        if end_at and end_at > now:
            upcoming.append(reservation)
        else:
            past.append(reservation)
    return upcoming, past


def _categorise_invoices(
    reservations: Sequence[Reservation],
) -> tuple[list[Invoice], list[Invoice]]:
    unpaid: dict[uuid.UUID, Invoice] = {}
    paid: dict[uuid.UUID, Invoice] = {}
    for reservation in reservations:
        if reservation.invoice is None:
            continue
        invoice = reservation.invoice
        if invoice.status == InvoiceStatus.PENDING:
            unpaid[invoice.id] = invoice
        elif invoice.status == InvoiceStatus.PAID:
            paid[invoice.id] = invoice
    sorted_unpaid = sorted(
        unpaid.values(), key=lambda inv: inv.created_at, reverse=True
    )
    sorted_paid = sorted(
        paid.values(), key=lambda inv: inv.paid_at or inv.updated_at, reverse=True
    )[:10]
    return sorted_unpaid, sorted_paid


@router.post("/login", response_model=PortalLoginResponse, summary="Portal login")
async def portal_login(
    payload: PortalLoginRequest,
    session: AsyncSession = Depends(deps.get_db_session),
) -> PortalLoginResponse:
    user = await authenticate_user(
        session, email=payload.email.lower(), password=payload.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.role != UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access is restricted to pet parents",
        )
    token = await create_access_token_for_user(user)
    return PortalLoginResponse(access_token=token)


@router.post(
    "/register_owner",
    response_model=PortalRegisterOwnerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Portal owner self-registration",
)
async def portal_register_owner(
    payload: PortalRegisterOwnerRequest,
    session: AsyncSession = Depends(deps.get_db_session),
) -> PortalRegisterOwnerResponse:
    account = await _resolve_account(session, explicit_slug=payload.account_slug)
    try:
        owner = await owner_service.create_owner(
            session,
            account_id=account.id,
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
            preferred_contact_method=None,
            notes=None,
            is_primary_contact=False,
        )
    except Exception as exc:  # IntegrityError handled generically
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        ) from exc
    token = await create_access_token_for_user(owner.user)
    return PortalRegisterOwnerResponse(
        owner=OwnerRead.model_validate(owner),
        access_token=token,
    )


@router.get("/me", response_model=PortalMeResponse, summary="Portal owner snapshot")
async def portal_me(
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PortalMeResponse:
    owner = await _ensure_portal_owner(session, current_user)
    pets = await _load_owner_pets(
        session, account_id=current_user.account_id, owner_id=owner.id
    )
    reservations = await _load_owner_reservations(
        session, account_id=current_user.account_id, owner_id=owner.id
    )
    upcoming, past = _categorise_reservations(reservations)
    unpaid, paid = _categorise_invoices(reservations)
    return PortalMeResponse(
        owner=OwnerRead.model_validate(owner),
        pets=[PetRead.model_validate(pet) for pet in pets],
        upcoming_reservations=[ReservationRead.model_validate(res) for res in upcoming],
        past_reservations=[ReservationRead.model_validate(res) for res in past],
        unpaid_invoices=[InvoiceRead.model_validate(inv) for inv in unpaid],
        recent_paid_invoices=[InvoiceRead.model_validate(inv) for inv in paid],
    )


async def _ensure_pet_for_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    pet_id: uuid.UUID,
) -> Pet:
    stmt = (
        select(Pet)
        .options(selectinload(Pet.owner).selectinload(OwnerProfile.user))
        .where(Pet.id == pet_id)
    )
    result = await session.execute(stmt)
    pet = result.scalar_one_or_none()
    if (
        pet is None
        or pet.owner_id != owner_id
        or pet.owner.user.account_id != account_id
    ):  # type: ignore[union-attr]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found for owner"
        )
    return pet


async def _resolve_location_id(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet: Pet,
    explicit_location_id: uuid.UUID | None,
) -> uuid.UUID:
    if explicit_location_id is not None:
        return explicit_location_id
    if pet.home_location_id is not None:
        return pet.home_location_id
    result = await session.execute(
        select(Location.id)
        .where(Location.account_id == account_id)
        .order_by(Location.created_at.asc())
        .limit(1)
    )
    location_id = result.scalar_one_or_none()
    if location_id is not None:
        return location_id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to determine reservation location",
    )


@router.post(
    "/reservations/request",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Portal reservation request",
)
async def portal_request_reservation(
    payload: PortalReservationRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> ReservationRead:
    owner = await _ensure_portal_owner(session, current_user)
    pet = await _ensure_pet_for_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner.id,
        pet_id=payload.pet_id,
    )
    location_id = await _resolve_location_id(
        session,
        account_id=current_user.account_id,
        pet=pet,
        explicit_location_id=payload.location_id,
    )
    try:
        reservation = await reservation_service.create_reservation(
            session,
            account_id=current_user.account_id,
            pet_id=pet.id,
            location_id=location_id,
            reservation_type=payload.reservation_type,
            start_at=payload.start_at,
            end_at=payload.end_at,
            base_rate=Decimal("0"),
            status=ReservationStatus.REQUESTED,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReservationRead.model_validate(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationRead,
    summary="Portal reservation cancel",
)
async def portal_cancel_reservation(
    reservation_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> ReservationRead:
    owner = await _ensure_portal_owner(session, current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if (
        reservation is None
        or reservation.pet.owner_id != owner.id
        or reservation.pet.owner.user.id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    try:
        updated = await reservation_service.update_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
            status=ReservationStatus.CANCELED,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReservationRead.model_validate(updated)


@router.get(
    "/invoices",
    response_model=PortalInvoicesResponse,
    summary="Portal invoices overview",
)
async def portal_invoices(
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PortalInvoicesResponse:
    owner = await _ensure_portal_owner(session, current_user)
    reservations = await _load_owner_reservations(
        session, account_id=current_user.account_id, owner_id=owner.id
    )
    unpaid, paid = _categorise_invoices(reservations)
    return PortalInvoicesResponse(
        unpaid=[InvoiceRead.model_validate(inv) for inv in unpaid],
        recent_paid=[InvoiceRead.model_validate(inv) for inv in paid],
    )


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceRead,
    summary="Portal invoice detail",
)
async def portal_invoice_detail(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> InvoiceRead:
    owner = await _ensure_portal_owner(session, current_user)
    invoice = await billing_service.get_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=invoice_id,
    )
    if (
        invoice is None
        or invoice.reservation is None
        or invoice.reservation.pet.owner_id != owner.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return InvoiceRead.model_validate(invoice)


@router.post(
    "/payments/create-intent",
    response_model=PortalPaymentIntentResponse,
    summary="Portal payment intent",
)
async def portal_create_payment_intent(
    payload: PortalPaymentIntentRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    stripe_client: StripeClient | None = Depends(_optional_stripe_client),
    current_user: User = Depends(deps.get_current_active_user),
) -> PortalPaymentIntentResponse:
    owner = await _ensure_portal_owner(session, current_user)
    invoice = await billing_service.get_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=payload.invoice_id,
    )
    if (
        invoice is None
        or invoice.reservation is None
        or invoice.reservation.pet.owner_id != owner.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already paid"
        )
    if stripe_client is None:
        fake_id = f"pi_{uuid.uuid4().hex}"
        client_secret = f"{fake_id}_secret_test"
        intent_id = fake_id
    else:
        try:
            intent = stripe_client.create_payment_intent(
                amount=invoice.total or Decimal("0"),
                invoice_id=invoice.id,
                metadata={"account_id": str(invoice.account_id)},
            )
            client_secret = intent.client_secret or f"{intent.id}_secret"
            intent_id = intent.id
        except StripeClientError:
            fake_id = f"pi_{uuid.uuid4().hex}"
            client_secret = f"{fake_id}_secret_test"
            intent_id = fake_id
    return PortalPaymentIntentResponse(
        client_secret=client_secret,
        transaction_id=intent_id,
        invoice_id=payload.invoice_id,
    )


@router.post(
    "/documents/presign",
    response_model=PortalDocumentPresignResponse,
    summary="Portal document presign stub",
)
async def portal_document_presign(
    payload: PortalDocumentPresignRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PortalDocumentPresignResponse:
    owner = await _ensure_portal_owner(session, current_user)
    if payload.owner_id is not None and payload.owner_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload for another owner",
        )
    if payload.pet_id is not None:
        await _ensure_pet_for_owner(
            session,
            account_id=current_user.account_id,
            owner_id=owner.id,
            pet_id=payload.pet_id,
        )
    upload_ref = uuid.uuid4().hex
    _PRESIGNED_UPLOADS[upload_ref] = {
        "file_name": payload.filename,
        "content_type": payload.content_type,
        "owner_id": str(payload.owner_id) if payload.owner_id else "",
        "pet_id": str(payload.pet_id) if payload.pet_id else "",
    }
    return PortalDocumentPresignResponse(
        upload_ref=upload_ref,
        upload_url=f"https://uploads.local/{upload_ref}",
        headers={"Content-Type": payload.content_type},
    )


@router.post(
    "/documents/finalize",
    response_model=PortalDocumentFinalizeResponse,
    summary="Portal document finalize",
)
async def portal_document_finalize(
    payload: PortalDocumentFinalizeRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PortalDocumentFinalizeResponse:
    owner = await _ensure_portal_owner(session, current_user)
    pending = _PRESIGNED_UPLOADS.pop(payload.upload_ref, None)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Upload reference not found"
        )
    owner_id = payload.owner_id or (
        uuid.UUID(pending["owner_id"]) if pending["owner_id"] else owner.id
    )
    pet_id = payload.pet_id or (
        uuid.UUID(pending["pet_id"]) if pending["pet_id"] else None
    )
    if owner_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot finalize for another owner",
        )
    if pet_id is not None:
        await _ensure_pet_for_owner(
            session,
            account_id=current_user.account_id,
            owner_id=owner.id,
            pet_id=pet_id,
        )
    document = await document_service.create_document(
        session,
        account_id=current_user.account_id,
        uploaded_by_user_id=current_user.id,
        payload=DocumentCreate(
            owner_id=owner_id,
            pet_id=pet_id,
            file_name=pending["file_name"],
            content_type=pending["content_type"],
            url=f"https://uploads.local/{payload.upload_ref}",
            notes=None,
        ),
    )
    return PortalDocumentFinalizeResponse(
        document=DocumentRead.model_validate(document)
    )
