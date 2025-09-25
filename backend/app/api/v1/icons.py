"""Icon management endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas import (
    IconCreate,
    IconRead,
    IconUpdate,
    OwnerIconAssignmentCreate,
    OwnerIconAssignmentRead,
    PetIconAssignmentCreate,
    PetIconAssignmentRead,
)
from app.services import icon_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get("", response_model=list[IconRead], summary="List icons")
async def list_icons(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[IconRead]:
    _assert_staff(current_user)
    icons = await icon_service.list_icons(session, account_id=current_user.account_id)
    return [IconRead.model_validate(icon) for icon in icons]


@router.post(
    "",
    response_model=IconRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create icon",
)
async def create_icon(
    payload: IconCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> IconRead:
    _assert_staff(current_user)
    icon = await icon_service.create_icon(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return IconRead.model_validate(icon)


@router.patch("/{icon_id}", response_model=IconRead, summary="Update icon")
async def update_icon(
    icon_id: uuid.UUID,
    payload: IconUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> IconRead:
    _assert_staff(current_user)
    icon = await icon_service.get_icon(
        session, account_id=current_user.account_id, icon_id=icon_id
    )
    if icon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Icon not found"
        )
    updated = await icon_service.update_icon(
        session,
        icon=icon,
        payload=payload,
        account_id=current_user.account_id,
    )
    return IconRead.model_validate(updated)


@router.delete(
    "/{icon_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete icon"
)
async def delete_icon(
    icon_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    icon = await icon_service.get_icon(
        session, account_id=current_user.account_id, icon_id=icon_id
    )
    if icon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Icon not found"
        )
    await icon_service.delete_icon(session, icon=icon)
    return None


@router.get(
    "/owners",
    response_model=list[OwnerIconAssignmentRead],
    summary="List owner icon assignments",
)
async def list_owner_icons(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: uuid.UUID | None = Query(default=None),
) -> list[OwnerIconAssignmentRead]:
    _assert_staff(current_user)
    assignments = await icon_service.list_owner_assignments(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    return [OwnerIconAssignmentRead.model_validate(item) for item in assignments]


@router.post(
    "/owners",
    response_model=OwnerIconAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign icon to owner",
)
async def assign_icon_to_owner(
    payload: OwnerIconAssignmentCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> OwnerIconAssignmentRead:
    _assert_staff(current_user)
    assignment = await icon_service.assign_icon_to_owner(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return OwnerIconAssignmentRead.model_validate(assignment)


@router.delete(
    "/owners/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove owner icon assignment",
)
async def remove_owner_icon(
    assignment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    assignment = await icon_service.get_owner_icon_assignment(
        session,
        account_id=current_user.account_id,
        assignment_id=assignment_id,
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner icon assignment not found",
        )
    await icon_service.remove_owner_icon(session, assignment=assignment)
    return None


@router.get(
    "/pets",
    response_model=list[PetIconAssignmentRead],
    summary="List pet icon assignments",
)
async def list_pet_icons(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    pet_id: uuid.UUID | None = Query(default=None),
) -> list[PetIconAssignmentRead]:
    _assert_staff(current_user)
    assignments = await icon_service.list_pet_assignments(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
    )
    return [PetIconAssignmentRead.model_validate(item) for item in assignments]


@router.post(
    "/pets",
    response_model=PetIconAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign icon to pet",
)
async def assign_icon_to_pet(
    payload: PetIconAssignmentCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PetIconAssignmentRead:
    _assert_staff(current_user)
    assignment = await icon_service.assign_icon_to_pet(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return PetIconAssignmentRead.model_validate(assignment)


@router.delete(
    "/pets/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove pet icon assignment",
)
async def remove_pet_icon(
    assignment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    assignment = await icon_service.get_pet_icon_assignment(
        session,
        account_id=current_user.account_id,
        assignment_id=assignment_id,
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet icon assignment not found",
        )
    await icon_service.remove_pet_icon(session, assignment=assignment)
    return None
