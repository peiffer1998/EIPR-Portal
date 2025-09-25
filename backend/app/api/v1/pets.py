"""Pet management API."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.pet import PetCreate, PetRead, PetUpdate
from app.services import pet_service

router = APIRouter()


def _assert_staff_authority(user: User) -> None:
    """Ensure the current user can manage pets."""
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[PetRead], summary="List pets")
async def list_pets(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[PetRead]:
    """Return pets for the authenticated user's account."""
    _assert_staff_authority(current_user)
    pets = await pet_service.list_pets(
        session,
        account_id=current_user.account_id,
        skip=skip,
        limit=min(limit, 100),
    )
    return [PetRead.model_validate(pet) for pet in pets]


@router.post("", response_model=PetRead, status_code=status.HTTP_201_CREATED, summary="Create pet")
async def create_pet(
    payload: PetCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PetRead:
    """Create a pet profile."""
    _assert_staff_authority(current_user)
    try:
        pet = await pet_service.create_pet(
            session,
            account_id=current_user.account_id,
            **payload.model_dump(),
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create pet") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related resource not found",
        ) from exc
    return PetRead.model_validate(pet)


@router.get("/{pet_id}", response_model=PetRead, summary="Get pet")
async def get_pet(
    pet_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PetRead:
    """Fetch a pet profile."""
    _assert_staff_authority(current_user)
    pet = await pet_service.get_pet(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
    )
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return PetRead.model_validate(pet)


@router.patch("/{pet_id}", response_model=PetRead, summary="Update pet")
async def update_pet(
    pet_id: uuid.UUID,
    payload: PetUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PetRead:
    """Update a pet profile."""
    _assert_staff_authority(current_user)
    pet = await pet_service.get_pet(
        session,
        account_id=current_user.account_id,
        pet_id=pet_id,
    )
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    try:
        updated_pet = await pet_service.update_pet(
            session,
            pet=pet,
            account_id=current_user.account_id,
            **payload.model_dump(exclude_unset=True),
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update pet") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related resource not found",
        ) from exc
    return PetRead.model_validate(updated_pet)
