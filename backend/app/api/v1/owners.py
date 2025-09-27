"""Owner management API."""

from __future__ import annotations

from decimal import Decimal
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.reservation import ReservationStatus
from app.models.user import User, UserRole
from app.schemas.owner import (
    OwnerCreate,
    OwnerNoteCreate,
    OwnerNoteRead,
    OwnerRead,
    OwnerUpdate,
    OwnerReservationRequest,
)
from app.schemas.reservation import ReservationRead
from app.schemas.store import MembershipRead, PackageBalanceRead
from app.security.permissions import require_roles
from app.services import (
    notification_service,
    note_buffer,
    owner_service,
    packages_service,
    pet_service,
    reservation_service,
)

router = APIRouter()

_ALLOWED_STAFF_ROLES = {
    UserRole.SUPERADMIN,
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.STAFF,
}


def _assert_staff_authority(user: User) -> None:
    """Ensure the current user can manage owners."""
    require_roles(user, _ALLOWED_STAFF_ROLES)


@router.get("", response_model=list[OwnerRead], summary="List owners")
async def list_owners(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
    q: str | None = Query(default=None, alias="q"),
) -> list[OwnerRead]:
    """Return owners for the authenticated user's account."""
    _assert_staff_authority(current_user)
    owners = await owner_service.list_owners(
        session,
        account_id=current_user.account_id,
        skip=skip,
        limit=min(limit, 100),
        search=q,
    )
    return [OwnerRead.model_validate(owner) for owner in owners]


@router.post(
    "",
    response_model=OwnerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create owner",
)
async def create_owner(
    payload: OwnerCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> OwnerRead:
    """Create a new pet parent and owner profile."""
    _assert_staff_authority(current_user)
    try:
        owner = await owner_service.create_owner(
            session,
            account_id=current_user.account_id,
            **payload.model_dump(),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
        ) from exc
    return OwnerRead.model_validate(owner)


@router.get("/{owner_id}", response_model=OwnerRead, summary="Get owner")
async def get_owner(
    owner_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> OwnerRead:
    """Fetch a single owner profile."""
    _assert_staff_authority(current_user)
    owner = await owner_service.get_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    return OwnerRead.model_validate(owner)


@router.get(
    "/{owner_id}/memberships",
    response_model=list[MembershipRead],
    summary="List memberships for an owner",
)
async def list_owner_memberships(
    owner_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[MembershipRead]:
    """Placeholder owner memberships endpoint."""
    _assert_staff_authority(current_user)
    _ = owner_id  # acknowledged
    return []


@router.get(
    "/{owner_id}/notes",
    response_model=list[OwnerNoteRead],
    summary="List notes for an owner",
)
async def list_owner_notes(
    owner_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[OwnerNoteRead]:
    owner = await owner_service.get_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    if current_user.role == UserRole.PET_PARENT and owner.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    entries = note_buffer.list_owner_notes(owner_id)
    return [OwnerNoteRead.model_validate(entry) for entry in entries]


@router.post(
    "/{owner_id}/notes",
    response_model=OwnerNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note for an owner",
)
async def add_owner_note(
    owner_id: uuid.UUID,
    payload: OwnerNoteCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> OwnerNoteRead:
    _assert_staff_authority(current_user)
    owner = await owner_service.get_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    note = note_buffer.add_owner_note(
        owner_id,
        text=payload.text,
        author_id=current_user.id,
    )
    return OwnerNoteRead.model_validate(note)


@router.get(
    "/{owner_id}/packages",
    response_model=list[PackageBalanceRead],
    summary="List remaining package balances for an owner",
)
async def list_owner_packages(
    owner_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[PackageBalanceRead]:
    """Return aggregated package balances for a specific owner."""
    _assert_staff_authority(current_user)
    owner = await owner_service.get_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    balances = await packages_service.remaining_credits(
        session,
        owner_id=owner.id,
        account_id=current_user.account_id,
    )
    return [PackageBalanceRead.model_validate(balance) for balance in balances]


@router.patch("/{owner_id}", response_model=OwnerRead, summary="Update owner")
async def update_owner(
    owner_id: uuid.UUID,
    payload: OwnerUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> OwnerRead:
    """Update mutable owner fields."""
    _assert_staff_authority(current_user)
    owner = await owner_service.get_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )

    try:
        updated_owner = await owner_service.update_owner(
            session,
            owner=owner,
            account_id=current_user.account_id,
            **payload.model_dump(exclude_unset=True),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
        ) from exc
    return OwnerRead.model_validate(updated_owner)


@router.post(
    "/{owner_id}/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Owner reservation request",
)
async def owner_create_reservation(
    owner_id: uuid.UUID,
    payload: OwnerReservationRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> ReservationRead:
    account_id = current_user.account_id
    owner = None
    if current_user.role == UserRole.PET_PARENT:
        owner = await owner_service.get_owner_by_user(session, user_id=current_user.id)
        if owner is None or owner.id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
            )
    else:
        _assert_staff_authority(current_user)
        owner = await owner_service.get_owner(
            session,
            account_id=account_id,
            owner_id=owner_id,
        )
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
            )

    pet = await pet_service.get_pet(
        session,
        account_id=account_id,
        pet_id=payload.pet_id,
    )
    if pet is None or pet.owner_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found for owner"
        )

    try:
        reservation = await reservation_service.create_reservation(
            session,
            account_id=account_id,
            pet_id=payload.pet_id,
            location_id=payload.location_id,
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
    notification_service.notify_booking_confirmation(reservation, background_tasks)
    return ReservationRead.model_validate(reservation)
