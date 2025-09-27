"""Pet management service helpers."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence, cast

from sqlalchemy import func, or_, select
from sqlalchemy.sql import Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet, PetType
from app.models.user import User
from app.models.immunization import ImmunizationRecord
from app.models.icon import PetIcon


def _base_pet_query(account_id: uuid.UUID) -> Select[tuple[Pet]]:
    """Return a base query for pets scoped to an account."""
    return (
        select(Pet)
        .join(Pet.owner)
        .join(OwnerProfile.user)
        .options(
            selectinload(Pet.owner).selectinload(OwnerProfile.user),
            selectinload(Pet.immunization_records).selectinload(
                ImmunizationRecord.immunization_type
            ),
            selectinload(Pet.icon_assignments).selectinload(PetIcon.icon),
        )
        .where(User.account_id == account_id)
        .order_by(Pet.created_at.desc())
    )


async def list_pets(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    owner_id: uuid.UUID | None = None,
    search: str | None = None,
) -> Sequence[Pet]:
    """Return paginated pets for an account."""
    stmt = _base_pet_query(account_id)
    if owner_id is not None:
        stmt = stmt.where(Pet.owner_id == owner_id)
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Pet.name).like(pattern),
                func.lower(User.first_name).like(pattern),
                func.lower(User.last_name).like(pattern),
                func.lower(User.email).like(pattern),
                func.lower(func.coalesce(User.phone_number, "")).like(pattern),
                func.lower(func.coalesce(Pet.breed, "")).like(pattern),
            )
        )
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
) -> Pet | None:
    """Return a single pet scoped to the account."""
    stmt = _base_pet_query(account_id).where(Pet.id == pet_id)
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _validate_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> OwnerProfile:
    owner = await session.get(
        OwnerProfile,
        owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user.account_id != account_id:
        raise ValueError("Owner does not belong to the provided account")
    return owner


async def _validate_location(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> None:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location does not belong to the provided account")


async def create_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    home_location_id: uuid.UUID | None,
    name: str,
    pet_type: PetType,
    breed: str | None,
    color: str | None,
    date_of_birth: date | None,
    notes: str | None,
) -> Pet:
    """Create a pet profile scoped to an account."""
    owner = await _validate_owner(session, account_id=account_id, owner_id=owner_id)
    if home_location_id is not None:
        await _validate_location(
            session, account_id=account_id, location_id=home_location_id
        )

    pet = Pet(
        owner_id=owner.id,
        home_location_id=home_location_id,
        name=name,
        pet_type=pet_type,
        breed=breed,
        color=color,
        date_of_birth=date_of_birth,
        notes=notes,
    )
    session.add(pet)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(pet)
    await session.refresh(pet, attribute_names=["owner"])
    await session.refresh(pet, attribute_names=["immunization_records"])
    await session.refresh(pet, attribute_names=["icon_assignments"])
    return pet


async def update_pet(
    session: AsyncSession,
    *,
    pet: Pet,
    account_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
    home_location_id: uuid.UUID | None = None,
    name: str | None = None,
    pet_type: PetType | None = None,
    breed: str | None = None,
    color: str | None = None,
    date_of_birth: date | None = None,
    notes: str | None = None,
) -> Pet:
    """Update an existing pet profile."""
    owner = pet.owner
    if owner.user.account_id != account_id:
        raise ValueError("Pet does not belong to the provided account")

    if owner_id is not None and owner_id != pet.owner_id:
        owner = await _validate_owner(session, account_id=account_id, owner_id=owner_id)
        pet.owner_id = owner.id

    if home_location_id is not None:
        await _validate_location(
            session, account_id=account_id, location_id=home_location_id
        )
        pet.home_location_id = home_location_id

    if name is not None:
        pet.name = name
    if pet_type is not None:
        pet.pet_type = pet_type
    if breed is not None:
        pet.breed = breed
    if color is not None:
        pet.color = color
    if date_of_birth is not None:
        pet.date_of_birth = cast(date, date_of_birth)  # type: ignore[assignment]
    if notes is not None:
        pet.notes = notes

    session.add(pet)
    await session.commit()
    await session.refresh(pet)
    await session.refresh(pet, attribute_names=["owner"])
    await session.refresh(pet, attribute_names=["immunization_records"])
    await session.refresh(pet, attribute_names=["icon_assignments"])
    return pet
