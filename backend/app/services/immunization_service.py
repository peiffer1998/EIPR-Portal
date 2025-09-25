"""Business logic for immunization tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, date
from typing import Sequence

from fastapi import BackgroundTasks
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.immunization import (
    ImmunizationRecord,
    ImmunizationStatus,
    ImmunizationType,
)
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.user import User
from app.schemas.document import DocumentCreate
from app.schemas.immunization import (
    ImmunizationRecordCreate,
    ImmunizationRecordUpdate,
    ImmunizationTypeCreate,
    ImmunizationTypeUpdate,
)
from app.services import document_service, notification_service


def _determine_status(
    *,
    expires_on: date | None,
    reminder_days: int,
) -> ImmunizationStatus:
    today = date.today()
    if not expires_on:
        return ImmunizationStatus.VALID
    if expires_on < today:
        return ImmunizationStatus.EXPIRED
    if expires_on <= today + timedelta(days=reminder_days):
        return ImmunizationStatus.EXPIRING
    return ImmunizationStatus.VALID


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
    return result.scalars().unique().all()


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
        description=payload.description,
        validity_days=payload.validity_days,
        reminder_days_before=payload.reminder_days_before,
        is_required=payload.is_required,
    )
    session.add(immunization_type)
    await session.commit()
    await session.refresh(immunization_type)
    return immunization_type


async def update_immunization_type(
    session: AsyncSession,
    *,
    immunization_type: ImmunizationType,
    payload: ImmunizationTypeUpdate,
) -> ImmunizationType:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(immunization_type, field, value)
    session.add(immunization_type)
    await session.commit()
    await session.refresh(immunization_type)
    return immunization_type


async def delete_immunization_type(
    session: AsyncSession,
    *,
    immunization_type: ImmunizationType,
) -> None:
    await session.delete(immunization_type)
    await session.commit()


async def _maybe_create_document(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID | None,
    document_payload: DocumentCreate | None,
) -> Document | None:
    if document_payload is None:
        return None
    return await document_service.create_document(
        session,
        account_id=account_id,
        uploaded_by_user_id=uploaded_by_user_id,
        payload=document_payload,
    )


async def create_immunization_record(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: ImmunizationRecordCreate,
    uploaded_by_user_id: uuid.UUID | None,
) -> ImmunizationRecord:
    immunization_type = await get_immunization_type(
        session, account_id=account_id, type_id=payload.immunization_type_id
    )
    if immunization_type is None:
        raise ValueError("Immunization type not found for account")

    pet = await session.get(
        Pet,
        payload.pet_id,
        options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
    )
    if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Pet not found for account")

    document = await _maybe_create_document(
        session,
        account_id=account_id,
        uploaded_by_user_id=uploaded_by_user_id,
        document_payload=payload.document,
    )

    status = _determine_status(
        expires_on=payload.expires_on,
        reminder_days=immunization_type.reminder_days_before,
    )

    record = ImmunizationRecord(
        account_id=account_id,
        pet_id=payload.pet_id,
        immunization_type_id=payload.immunization_type_id,
        document_id=document.id if document else payload.document_id,
        received_on=payload.received_on,
        expires_on=payload.expires_on,
        notes=payload.notes,
        status=status,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_immunization_record(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    record_id: uuid.UUID,
) -> ImmunizationRecord | None:
    stmt = (
        select(ImmunizationRecord)
        .options(
            selectinload(ImmunizationRecord.immunization_type),
            selectinload(ImmunizationRecord.document),
        )
        .where(
            ImmunizationRecord.account_id == account_id,
            ImmunizationRecord.id == record_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def list_immunization_records(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID | None = None,
    status: ImmunizationStatus | None = None,
) -> Sequence[ImmunizationRecord]:
    stmt = (
        select(ImmunizationRecord)
        .options(
            selectinload(ImmunizationRecord.immunization_type),
            selectinload(ImmunizationRecord.document),
        )
        .where(ImmunizationRecord.account_id == account_id)
        .order_by(ImmunizationRecord.received_on.desc())
    )
    if pet_id is not None:
        stmt = stmt.where(ImmunizationRecord.pet_id == pet_id)
    if status is not None:
        stmt = stmt.where(ImmunizationRecord.status == status)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def update_immunization_record(
    session: AsyncSession,
    *,
    record: ImmunizationRecord,
    payload: ImmunizationRecordUpdate,
    account_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID | None,
) -> ImmunizationRecord:
    if record.account_id != account_id:
        raise ValueError("Immunization record does not belong to the provided account")

    updates = payload.model_dump(exclude_unset=True)
    if "document_id" in updates:
        record.document_id = updates.pop("document_id")
    if payload.notes is not None:
        record.notes = payload.notes
    if payload.received_on is not None:
        record.received_on = payload.received_on
    if payload.expires_on is not None:
        record.expires_on = payload.expires_on
    if payload.status is not None:
        record.status = payload.status

    if payload.status is None and (payload.expires_on is not None):
        record.status = _determine_status(
            expires_on=record.expires_on,
            reminder_days=record.immunization_type.reminder_days_before,
        )

    if payload.document is not None:
        # allow updating document metadata via payload
        document = await _maybe_create_document(
            session,
            account_id=account_id,
            uploaded_by_user_id=uploaded_by_user_id,
            document_payload=payload.document,
        )
        record.document_id = document.id if document else record.document_id

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def delete_immunization_record(
    session: AsyncSession,
    *,
    record: ImmunizationRecord,
) -> None:
    await session.delete(record)
    await session.commit()


async def evaluate_immunizations(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    background_tasks: BackgroundTasks | None = None,
) -> list[ImmunizationRecord]:
    today = datetime.now(UTC)
    stmt = (
        select(ImmunizationRecord)
        .options(
            selectinload(ImmunizationRecord.immunization_type),
            selectinload(ImmunizationRecord.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
        )
        .where(ImmunizationRecord.account_id == account_id)
    )
    result = await session.execute(stmt)
    records = result.scalars().unique().all()
    updated: list[ImmunizationRecord] = []
    for record in records:
        immunization_type = record.immunization_type
        new_status = _determine_status(
            expires_on=record.expires_on,
            reminder_days=immunization_type.reminder_days_before,
        )
        if record.status != new_status:
            record.status = new_status
            updated.append(record)
        record.last_evaluated_at = today

        should_notify = False
        if new_status in (ImmunizationStatus.EXPIRING, ImmunizationStatus.EXPIRED):
            if (
                not record.reminder_sent_at
                or record.reminder_sent_at.date() < today.date()
            ):
                should_notify = True
        if should_notify and background_tasks is not None:
            owner_user: User | None = None
            if record.pet.owner:
                owner_user = record.pet.owner.user
            if owner_user:
                notification_service.notify_immunization_alert(
                    record=record,
                    owner_user=owner_user,
                    background_tasks=background_tasks,
                )
                record.reminder_sent_at = today
    session.add_all(records)
    await session.commit()
    return updated
