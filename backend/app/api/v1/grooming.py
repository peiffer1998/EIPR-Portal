"""Staff-facing grooming administration API."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models import (
    GroomingAddon,
    GroomingAppointment,
    GroomingService,
    Location,
    Specialist,
    SpecialistSchedule,
    SpecialistTimeOff,
    User,
    UserRole,
)
from app.schemas.grooming import (
    GroomingAddonCreate,
    GroomingAddonRead,
    GroomingAddonUpdate,
    GroomingAppointmentCancel,
    GroomingAppointmentCreate,
    GroomingAppointmentListItem,
    GroomingAppointmentRead,
    GroomingAppointmentReschedule,
    GroomingAppointmentStatusUpdate,
    GroomingAvailabilitySlot,
    GroomingServiceCreate,
    GroomingServiceRead,
    GroomingServiceUpdate,
    SpecialistCreate,
    SpecialistRead,
    SpecialistScheduleCreate,
    SpecialistScheduleRead,
    SpecialistTimeOffCreate,
    SpecialistTimeOffRead,
    SpecialistUpdate,
)
from app.services import grooming_booking_service, grooming_schedule_service

router = APIRouter()


def _assert_staff(current_user: User) -> None:
    if current_user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


async def _get_location(
    session: AsyncSession,
    *,
    location_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


async def _get_specialist(
    session: AsyncSession,
    *,
    specialist_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Specialist:
    specialist = await session.get(Specialist, specialist_id)
    if specialist is None or specialist.account_id != account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Specialist not found")
    return specialist


async def _get_service(
    session: AsyncSession,
    *,
    service_id: uuid.UUID,
    account_id: uuid.UUID,
) -> GroomingService:
    service = await session.get(GroomingService, service_id)
    if service is None or service.account_id != account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


async def _get_addon(
    session: AsyncSession,
    *,
    addon_id: uuid.UUID,
    account_id: uuid.UUID,
) -> GroomingAddon:
    addon = await session.get(GroomingAddon, addon_id)
    if addon is None or addon.account_id != account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Add-on not found")
    return addon


def _serialize_appointment(obj: GroomingAppointment) -> GroomingAppointmentRead:
    return GroomingAppointmentRead(
        id=obj.id,
        account_id=obj.account_id,
        owner_id=obj.owner_id,
        pet_id=obj.pet_id,
        specialist_id=obj.specialist_id,
        service_id=obj.service_id,
        start_at=obj.start_at,
        end_at=obj.end_at,
        status=obj.status,
        notes=obj.notes,
        price_snapshot=obj.price_snapshot,
        commission_type=obj.commission_type,
        commission_rate=obj.commission_rate,
        commission_amount=obj.commission_amount,
        invoice_id=obj.invoice_id,
        reservation_id=obj.reservation_id,
        addon_ids=[addon.id for addon in obj.addons],
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


@router.post(
    "/specialists",
    response_model=SpecialistRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create grooming specialist",
)
async def create_specialist(
    payload: SpecialistCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> SpecialistRead:
    _assert_staff(current_user)
    await _get_location(
        session, location_id=payload.location_id, account_id=current_user.account_id
    )
    specialist = Specialist(
        account_id=current_user.account_id,
        location_id=payload.location_id,
        name=payload.name,
        user_id=payload.user_id,
        commission_type=payload.commission_type,
        commission_rate=payload.commission_rate,
        active=payload.active,
    )
    session.add(specialist)
    await session.commit()
    await session.refresh(specialist)
    return SpecialistRead.model_validate(specialist)


@router.get(
    "/specialists",
    response_model=list[SpecialistRead],
    summary="List grooming specialists",
)
async def list_specialists(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[SpecialistRead]:
    _assert_staff(current_user)
    stmt: Select[tuple[Specialist]] = select(Specialist).where(
        Specialist.account_id == current_user.account_id
    )
    result = await session.execute(stmt)
    specialists = result.scalars().all()
    return [SpecialistRead.model_validate(obj) for obj in specialists]


@router.patch(
    "/specialists/{specialist_id}",
    response_model=SpecialistRead,
    summary="Update grooming specialist",
)
async def update_specialist(
    specialist_id: uuid.UUID,
    payload: SpecialistUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> SpecialistRead:
    _assert_staff(current_user)
    specialist = await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(specialist, key, value)
    await session.commit()
    await session.refresh(specialist)
    return SpecialistRead.model_validate(specialist)


@router.delete(
    "/specialists/{specialist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete grooming specialist",
)
async def delete_specialist(
    specialist_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    specialist = await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )
    await session.delete(specialist)
    await session.commit()


@router.post(
    "/services",
    response_model=GroomingServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create grooming service",
)
async def create_service(
    payload: GroomingServiceCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingServiceRead:
    _assert_staff(current_user)
    service = GroomingService(
        account_id=current_user.account_id,
        **payload.model_dump(),
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return GroomingServiceRead.model_validate(service)


@router.get(
    "/services",
    response_model=list[GroomingServiceRead],
    summary="List grooming services",
)
async def list_services(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[GroomingServiceRead]:
    _assert_staff(current_user)
    stmt: Select[tuple[GroomingService]] = select(GroomingService).where(
        GroomingService.account_id == current_user.account_id
    )
    result = await session.execute(stmt)
    services = result.scalars().all()
    return [GroomingServiceRead.model_validate(obj) for obj in services]


@router.patch(
    "/services/{service_id}",
    response_model=GroomingServiceRead,
    summary="Update grooming service",
)
async def update_service(
    service_id: uuid.UUID,
    payload: GroomingServiceUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingServiceRead:
    _assert_staff(current_user)
    service = await _get_service(
        session, service_id=service_id, account_id=current_user.account_id
    )
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(service, key, value)
    await session.commit()
    await session.refresh(service)
    return GroomingServiceRead.model_validate(service)


@router.post(
    "/addons",
    response_model=GroomingAddonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create grooming add-on",
)
async def create_addon(
    payload: GroomingAddonCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAddonRead:
    _assert_staff(current_user)
    addon = GroomingAddon(
        account_id=current_user.account_id,
        **payload.model_dump(),
    )
    session.add(addon)
    await session.commit()
    await session.refresh(addon)
    return GroomingAddonRead.model_validate(addon)


@router.get(
    "/addons",
    response_model=list[GroomingAddonRead],
    summary="List grooming add-ons",
)
async def list_addons(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[GroomingAddonRead]:
    _assert_staff(current_user)
    stmt: Select[tuple[GroomingAddon]] = select(GroomingAddon).where(
        GroomingAddon.account_id == current_user.account_id
    )
    result = await session.execute(stmt)
    addons = result.scalars().all()
    return [GroomingAddonRead.model_validate(obj) for obj in addons]


@router.patch(
    "/addons/{addon_id}",
    response_model=GroomingAddonRead,
    summary="Update grooming add-on",
)
async def update_addon(
    addon_id: uuid.UUID,
    payload: GroomingAddonUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAddonRead:
    _assert_staff(current_user)
    addon = await _get_addon(
        session, addon_id=addon_id, account_id=current_user.account_id
    )
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(addon, key, value)
    await session.commit()
    await session.refresh(addon)
    return GroomingAddonRead.model_validate(addon)


@router.post(
    "/specialists/{specialist_id}/schedules",
    response_model=SpecialistScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add specialist schedule block",
)
async def create_specialist_schedule(
    specialist_id: uuid.UUID,
    payload: SpecialistScheduleCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> SpecialistScheduleRead:
    _assert_staff(current_user)
    specialist = await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="End time must be after start"
        )
    schedule = SpecialistSchedule(
        account_id=current_user.account_id,
        specialist_id=specialist.id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    return SpecialistScheduleRead.model_validate(schedule)


@router.get(
    "/specialists/{specialist_id}/schedules",
    response_model=list[SpecialistScheduleRead],
    summary="List specialist schedules",
)
async def list_specialist_schedules(
    specialist_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[SpecialistScheduleRead]:
    _assert_staff(current_user)
    await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )
    stmt: Select[tuple[SpecialistSchedule]] = select(SpecialistSchedule).where(
        SpecialistSchedule.specialist_id == specialist_id
    )
    result = await session.execute(stmt)
    schedules = result.scalars().all()
    return [SpecialistScheduleRead.model_validate(obj) for obj in schedules]


@router.post(
    "/specialists/{specialist_id}/time-off",
    response_model=SpecialistTimeOffRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record specialist time off",
)
async def create_time_off(
    specialist_id: uuid.UUID,
    payload: SpecialistTimeOffCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> SpecialistTimeOffRead:
    _assert_staff(current_user)
    specialist = await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="End must follow start")
    entry = SpecialistTimeOff(
        account_id=current_user.account_id,
        specialist_id=specialist.id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        reason=payload.reason,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return SpecialistTimeOffRead.model_validate(entry)


@router.get(
    "/specialists/{specialist_id}/time-off",
    response_model=list[SpecialistTimeOffRead],
    summary="List specialist time off",
)
async def list_time_off(
    specialist_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[SpecialistTimeOffRead]:
    _assert_staff(current_user)
    await _get_specialist(
        session, specialist_id=specialist_id, account_id=current_user.account_id
    )
    stmt: Select[tuple[SpecialistTimeOff]] = select(SpecialistTimeOff).where(
        SpecialistTimeOff.specialist_id == specialist_id
    )
    result = await session.execute(stmt)
    entries = result.scalars().all()
    return [SpecialistTimeOffRead.model_validate(obj) for obj in entries]


@router.get(
    "/availability",
    response_model=list[GroomingAvailabilitySlot],
    summary="Find available grooming slots",
)
async def get_availability(
    *,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date,
    date_to: date,
    service_id: uuid.UUID,
    addons: Annotated[list[uuid.UUID], Query(default_factory=list)],
    specialist_id: uuid.UUID | None = None,
    location_id: uuid.UUID,
    slot_interval_minutes: int = 15,
) -> list[GroomingAvailabilitySlot]:
    _assert_staff(current_user)
    await _get_location(
        session, location_id=location_id, account_id=current_user.account_id
    )
    slots = await grooming_schedule_service.list_available_slots(
        session,
        account_id=current_user.account_id,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
        service_id=service_id,
        addon_ids=addons or [],
        specialist_id=specialist_id,
        slot_interval_minutes=slot_interval_minutes,
    )
    return [GroomingAvailabilitySlot.model_validate(slot) for slot in slots]


@router.post(
    "/appointments",
    response_model=GroomingAppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book grooming appointment",
)
async def create_appointment(
    payload: GroomingAppointmentCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAppointmentRead:
    _assert_staff(current_user)
    try:
        appointment = await grooming_booking_service.book_appointment(
            session,
            account_id=current_user.account_id,
            owner_id=payload.owner_id,
            pet_id=payload.pet_id,
            specialist_id=payload.specialist_id,
            service_id=payload.service_id,
            addon_ids=payload.addon_ids,
            start_at=payload.start_at,
            notes=payload.notes,
            reservation_id=payload.reservation_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_appointment(appointment)


@router.get(
    "/appointments",
    response_model=list[GroomingAppointmentListItem],
    summary="List grooming appointments",
)
async def list_appointments(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_filter: date | None = None,
    specialist_id: uuid.UUID | None = None,
) -> list[GroomingAppointmentListItem]:
    _assert_staff(current_user)
    stmt = (
        select(GroomingAppointment)
        .where(GroomingAppointment.account_id == current_user.account_id)
        .options(
            selectinload(GroomingAppointment.addons),
            selectinload(GroomingAppointment.service),
            selectinload(GroomingAppointment.specialist),
        )
        .order_by(GroomingAppointment.start_at)
    )
    if specialist_id is not None:
        stmt = stmt.where(GroomingAppointment.specialist_id == specialist_id)
    if date_filter is not None:
        window_start = datetime.combine(date_filter, time.min)
        window_end = datetime.combine(date_filter, time.max)
        stmt = stmt.where(
            GroomingAppointment.start_at >= window_start,
            GroomingAppointment.start_at <= window_end,
        )
    result = await session.execute(stmt)
    appointments = result.scalars().unique().all()
    items: list[GroomingAppointmentListItem] = []
    for appt in appointments:
        base = _serialize_appointment(appt)
        items.append(
            GroomingAppointmentListItem(
                **base.model_dump(),
                service_name=appt.service.name if appt.service else None,
                specialist_name=appt.specialist.name if appt.specialist else None,
            )
        )
    return items


@router.patch(
    "/appointments/{appointment_id}/reschedule",
    response_model=GroomingAppointmentRead,
    summary="Reschedule grooming appointment",
)
async def reschedule(
    appointment_id: uuid.UUID,
    payload: GroomingAppointmentReschedule,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAppointmentRead:
    _assert_staff(current_user)
    try:
        appointment = await grooming_booking_service.reschedule_appointment(
            session,
            account_id=current_user.account_id,
            appointment_id=appointment_id,
            new_start_at=payload.new_start_at,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_appointment(appointment)


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=GroomingAppointmentRead,
    summary="Cancel grooming appointment",
)
async def cancel(
    appointment_id: uuid.UUID,
    payload: GroomingAppointmentCancel,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAppointmentRead:
    _assert_staff(current_user)
    appointment = await grooming_booking_service.cancel_appointment(
        session,
        account_id=current_user.account_id,
        appointment_id=appointment_id,
        reason=payload.reason,
    )
    return _serialize_appointment(appointment)


@router.post(
    "/appointments/{appointment_id}/status",
    response_model=GroomingAppointmentRead,
    summary="Update grooming appointment status",
)
async def update_status(
    appointment_id: uuid.UUID,
    payload: GroomingAppointmentStatusUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GroomingAppointmentRead:
    _assert_staff(current_user)
    try:
        appointment = await grooming_booking_service.update_status(
            session,
            account_id=current_user.account_id,
            appointment_id=appointment_id,
            new_status=payload.new_status,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_appointment(appointment)
