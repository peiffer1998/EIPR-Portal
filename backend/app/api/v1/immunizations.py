"""Health track immunization API."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models import OwnerProfile, Pet, User, UserRole
from app.schemas import (
    ImmunizationRecordCreate,
    ImmunizationRecordStatus,
    ImmunizationTypeCreate,
    ImmunizationTypeRead,
)
from app.services import immunization_service

router = APIRouter()


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff permissions required",
        )


async def _load_pet(
    session: AsyncSession,
    *,
    pet_id: uuid.UUID,
    account_id: uuid.UUID,
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
        or pet.owner is None
        or pet.owner.user is None
        or pet.owner.user.account_id != account_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
        )
    return pet


async def _load_owner(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    account_id: uuid.UUID,
) -> OwnerProfile:
    stmt = (
        select(OwnerProfile)
        .options(selectinload(OwnerProfile.user))
        .where(OwnerProfile.id == owner_id)
    )
    result = await session.execute(stmt)
    owner = result.scalar_one_or_none()
    if owner is None or owner.user is None or owner.user.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found",
        )
    return owner


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
    _require_staff(current_user)
    created = await immunization_service.create_immunization_type(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return ImmunizationTypeRead.model_validate(created)


@router.get(
    "/types",
    response_model=list[ImmunizationTypeRead],
    summary="List immunization types",
)
async def list_types(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[ImmunizationTypeRead]:
    _require_staff(current_user)
    types = await immunization_service.list_immunization_types(
        session, account_id=current_user.account_id
    )
    return [ImmunizationTypeRead.model_validate(item) for item in types]


@router.post(
    "/pets/{pet_id}/immunizations",
    response_model=ImmunizationRecordStatus,
    status_code=status.HTTP_201_CREATED,
    summary="Create immunization record for pet",
)
async def create_pet_immunization(
    payload: ImmunizationRecordCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    pet_id: Annotated[uuid.UUID, Path()],
) -> ImmunizationRecordStatus:
    _require_staff(current_user)
    await _load_pet(session, pet_id=pet_id, account_id=current_user.account_id)
    record = await immunization_service.create_record_for_pet(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
        payload=payload,
        created_by=current_user,
    )
    statuses = await immunization_service.status_for_pet(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
    )
    for status_entry in statuses:
        if status_entry.record.id == record.id:
            return status_entry
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get(
    "/pets/{pet_id}/immunizations",
    response_model=list[ImmunizationRecordStatus],
    summary="List immunization statuses for pet",
)
async def list_pet_immunizations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    pet_id: Annotated[uuid.UUID, Path()],
) -> list[ImmunizationRecordStatus]:
    pet = await _load_pet(session, pet_id=pet_id, account_id=current_user.account_id)
    if current_user.role == UserRole.PET_PARENT:
        owner_profile = await deps.get_current_owner_profile(session, current_user)
        if owner_profile is None or owner_profile.id != pet.owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
            )

    return await immunization_service.status_for_pet(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
    )


@router.get(
    "/owners/{owner_id}/immunizations",
    response_model=list[ImmunizationRecordStatus],
    summary="List immunization statuses for owner",
)
async def list_owner_immunizations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: Annotated[uuid.UUID, Path()],
) -> list[ImmunizationRecordStatus]:
    owner = await _load_owner(
        session, owner_id=owner_id, account_id=current_user.account_id
    )
    if current_user.role == UserRole.PET_PARENT:
        owner_profile = await deps.get_current_owner_profile(session, current_user)
        if owner_profile is None or owner_profile.id != owner.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
            )

    return await immunization_service.status_for_owner(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
