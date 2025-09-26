"""Business logic for the health immunization track."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    ImmunizationRecord,
    ImmunizationStatus,
    ImmunizationType,
    OwnerProfile,
    Pet,
    User,
)
from app.schemas.immunization import (
    ImmunizationRecordCreate,
    ImmunizationRecordRead,
    ImmunizationRecordStatus,
    ImmunizationTypeCreate,
)

DEFAULT_EXPIRING_WINDOW_DAYS = 30


def compute_status(
    record: ImmunizationRecord,
    *,
    reference_date: date | None = None,
    expiring_window_days: int = DEFAULT_EXPIRING_WINDOW_DAYS,
) -> ImmunizationStatus:
    """Determine the appropriate status for a record."""

    today = reference_date or date.today()

    if record.verified_by_user_id is None:
        return ImmunizationStatus.PENDING

    if record.expires_on is None:
        return ImmunizationStatus.CURRENT

    if record.expires_on < today:
        return ImmunizationStatus.EXPIRED

    if record.expires_on <= today + timedelta(days=expiring_window_days):
        return ImmunizationStatus.EXPIRING

    return ImmunizationStatus.CURRENT


async def list_immunization_types(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Sequence[ImmunizationType]:
    stmt: Select[tuple[ImmunizationType]] = (
        select(ImmunizationType)
        .where(ImmunizationType.account_id == account_id)
        .order_by(ImmunizationType.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_immunization_type(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    type_id: uuid.UUID,
) -> ImmunizationType | None:
    stmt = select(ImmunizationType).where(
        ImmunizationType.account_id == account_id,
        ImmunizationType.id == type_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_immunization_type(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: ImmunizationTypeCreate,
) -> ImmunizationType:
    immunization_type = ImmunizationType(
        account_id=account_id,
        name=payload.name,
        required=payload.is_required,
        default_valid_days=payload.validity_days,
    )
    session.add(immunization_type)
    await session.commit()
    await session.refresh(immunization_type)
    return immunization_type


def _project_record_status(
    record: ImmunizationRecord,
    *,
    status: ImmunizationStatus,
) -> ImmunizationRecordStatus:
    record_read = ImmunizationRecordRead.model_validate(record)
    return ImmunizationRecordStatus(
        record=record_read,
        is_pending=status == ImmunizationStatus.PENDING,
        is_current=status == ImmunizationStatus.CURRENT,
        is_expiring=status == ImmunizationStatus.EXPIRING,
        is_expired=status == ImmunizationStatus.EXPIRED,
        is_required=record.immunization_type.required,
    )


def _maybe_apply_default_expiry(
    *,
    record: ImmunizationRecord,
    immunization_type: ImmunizationType,
) -> None:
    """Populate expires_on if omitted and type defines a validity window."""

    if record.expires_on is not None:
        return
    if immunization_type.default_valid_days is None:
        return
    record.expires_on = record.issued_on + timedelta(
        days=immunization_type.default_valid_days
    )


async def create_record_for_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
    payload: ImmunizationRecordCreate,
    created_by: User,
) -> ImmunizationRecord:
    immunization_type = await get_immunization_type(
        session, account_id=account_id, type_id=payload.type_id
    )
    if immunization_type is None:
        raise ValueError("Immunization type not found for account")

    pet = await session.get(
        Pet,
        pet_id,
        options=[joinedload(Pet.owner).joinedload(OwnerProfile.user)],
    )
    if pet is None or pet.owner is None or pet.owner.user is None:
        raise ValueError("Pet not found")
    if pet.owner.user.account_id != account_id:
        raise ValueError("Pet does not belong to account")

    record = ImmunizationRecord(
        account_id=account_id,
        pet_id=pet_id,
        type_id=payload.type_id,
        issued_on=payload.issued_on,
        expires_on=payload.expires_on,
        notes=payload.notes,
        verified_by_user_id=created_by.id if payload.verified else None,
    )

    _maybe_apply_default_expiry(record=record, immunization_type=immunization_type)

    record.status = compute_status(
        record,
        reference_date=payload.issued_on,
    )

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def status_for_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
    expiring_window_days: int = DEFAULT_EXPIRING_WINDOW_DAYS,
) -> list[ImmunizationRecordStatus]:
    stmt: Select[tuple[ImmunizationRecord]] = (
        select(ImmunizationRecord)
        .options(joinedload(ImmunizationRecord.immunization_type))
        .where(
            ImmunizationRecord.account_id == account_id,
            ImmunizationRecord.pet_id == pet_id,
        )
        .order_by(ImmunizationRecord.created_at.desc())
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    statuses: list[ImmunizationRecordStatus] = []
    dirty = False
    for record in records:
        status = compute_status(
            record,
            expiring_window_days=expiring_window_days,
        )
        if record.status != status:
            record.status = status
            dirty = True
        statuses.append(_project_record_status(record, status=status))

    if dirty:
        await session.commit()

    return statuses


async def status_for_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    expiring_window_days: int = DEFAULT_EXPIRING_WINDOW_DAYS,
) -> list[ImmunizationRecordStatus]:
    stmt = (
        select(ImmunizationRecord)
        .join(Pet, Pet.id == ImmunizationRecord.pet_id)
        .options(joinedload(ImmunizationRecord.immunization_type))
        .where(
            ImmunizationRecord.account_id == account_id,
            Pet.owner_id == owner_id,
        )
        .order_by(ImmunizationRecord.created_at.desc())
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    statuses: list[ImmunizationRecordStatus] = []
    dirty = False
    for record in records:
        status = compute_status(
            record,
            expiring_window_days=expiring_window_days,
        )
        if record.status != status:
            record.status = status
            dirty = True
        statuses.append(_project_record_status(record, status=status))

    if dirty:
        await session.commit()

    return statuses


async def recompute_for_account(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    expiring_window_days: int = DEFAULT_EXPIRING_WINDOW_DAYS,
) -> list[ImmunizationRecord]:
    stmt = (
        select(ImmunizationRecord)
        .options(joinedload(ImmunizationRecord.immunization_type))
        .where(ImmunizationRecord.account_id == account_id)
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    dirty_records: list[ImmunizationRecord] = []
    dirty = False
    for record in records:
        status = compute_status(
            record,
            expiring_window_days=expiring_window_days,
        )
        if record.status != status:
            record.status = status
            dirty_records.append(record)
            dirty = True

    if dirty:
        await session.commit()

    return dirty_records


async def get_owner_profile(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    account_id: uuid.UUID,
) -> OwnerProfile | None:
    stmt = (
        select(OwnerProfile)
        .join(OwnerProfile.user)
        .where(
            OwnerProfile.id == owner_id,
            User.account_id == account_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
