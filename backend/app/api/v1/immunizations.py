"""API endpoints for managing immunizations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas import (
    ImmunizationRecordCreate,
    ImmunizationRecordRead,
    ImmunizationRecordUpdate,
    ImmunizationTypeCreate,
    ImmunizationTypeRead,
    ImmunizationTypeUpdate,
)
from app.models.immunization import ImmunizationStatus
from app.services import immunization_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "/types",
    response_model=list[ImmunizationTypeRead],
    summary="List immunization types",
)
async def list_types(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[ImmunizationTypeRead]:
    _assert_staff(current_user)
    items = await immunization_service.list_immunization_types(
        session, account_id=current_user.account_id
    )
    return [ImmunizationTypeRead.model_validate(item) for item in items]


@router.post(
    "/types",
    response_model=ImmunizationTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create immunization type",
)
async def create_type(
    payload: ImmunizationTypeCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ImmunizationTypeRead:
    _assert_staff(current_user)
    record = await immunization_service.create_immunization_type(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return ImmunizationTypeRead.model_validate(record)


@router.patch(
    "/types/{type_id}",
    response_model=ImmunizationTypeRead,
    summary="Update immunization type",
)
async def update_type(
    type_id: uuid.UUID,
    payload: ImmunizationTypeUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ImmunizationTypeRead:
    _assert_staff(current_user)
    immunization_type = await immunization_service.get_immunization_type(
        session, account_id=current_user.account_id, type_id=type_id
    )
    if immunization_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Immunization type not found"
        )
    updated = await immunization_service.update_immunization_type(
        session,
        immunization_type=immunization_type,
        payload=payload,
    )
    return ImmunizationTypeRead.model_validate(updated)


@router.delete(
    "/types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete immunization type",
)
async def delete_type(
    type_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    immunization_type = await immunization_service.get_immunization_type(
        session, account_id=current_user.account_id, type_id=type_id
    )
    if immunization_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Immunization type not found"
        )
    await immunization_service.delete_immunization_type(
        session, immunization_type=immunization_type
    )
    return None


@router.get(
    "/records",
    response_model=list[ImmunizationRecordRead],
    summary="List immunization records",
)
async def list_records(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    pet_id: uuid.UUID | None = Query(default=None),
    status_filter: ImmunizationStatus | None = Query(default=None, alias="status"),
) -> list[ImmunizationRecordRead]:
    _assert_staff(current_user)
    records = await immunization_service.list_immunization_records(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
        status=status_filter,
    )
    return [ImmunizationRecordRead.model_validate(record) for record in records]


@router.post(
    "/records",
    response_model=ImmunizationRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create immunization record",
)
async def create_record(
    payload: ImmunizationRecordCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ImmunizationRecordRead:
    _assert_staff(current_user)
    record = await immunization_service.create_immunization_record(
        session,
        account_id=current_user.account_id,
        payload=payload,
        uploaded_by_user_id=current_user.id,
    )
    hydrated = await immunization_service.get_immunization_record(
        session, account_id=current_user.account_id, record_id=record.id
    )
    return ImmunizationRecordRead.model_validate(hydrated or record)


@router.patch(
    "/records/{record_id}",
    response_model=ImmunizationRecordRead,
    summary="Update immunization record",
)
async def update_record(
    record_id: uuid.UUID,
    payload: ImmunizationRecordUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ImmunizationRecordRead:
    _assert_staff(current_user)
    record = await immunization_service.get_immunization_record(
        session, account_id=current_user.account_id, record_id=record_id
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Immunization record not found",
        )
    updated = await immunization_service.update_immunization_record(
        session,
        record=record,
        payload=payload,
        account_id=current_user.account_id,
        uploaded_by_user_id=current_user.id,
    )
    hydrated = await immunization_service.get_immunization_record(
        session, account_id=current_user.account_id, record_id=updated.id
    )
    return ImmunizationRecordRead.model_validate(hydrated or updated)


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete immunization record",
)
async def delete_record(
    record_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    record = await immunization_service.get_immunization_record(
        session, account_id=current_user.account_id, record_id=record_id
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Immunization record not found",
        )
    await immunization_service.delete_immunization_record(session, record=record)
    return None


@router.post(
    "/evaluate",
    response_model=list[ImmunizationRecordRead],
    summary="Evaluate immunization statuses",
)
async def evaluate_immunizations(
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[ImmunizationRecordRead]:
    _assert_staff(current_user)
    updated = await immunization_service.evaluate_immunizations(
        session,
        account_id=current_user.account_id,
        background_tasks=background_tasks,
    )
    hydrated = [
        await immunization_service.get_immunization_record(
            session, account_id=current_user.account_id, record_id=record.id
        )
        or record
        for record in updated
    ]
    return [ImmunizationRecordRead.model_validate(record) for record in hydrated]
