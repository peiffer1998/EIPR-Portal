"""Services for managing custom icons and assignments."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.icon import Icon, OwnerIcon, PetIcon
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.schemas.icon import (
    IconCreate,
    IconUpdate,
    OwnerIconAssignmentCreate,
    PetIconAssignmentCreate,
)


async def list_icons(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Sequence[Icon]:
    stmt: Select[tuple[Icon]] = (
        select(Icon)
        .where(Icon.account_id == account_id)
        .order_by(Icon.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_icon(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    icon_id: uuid.UUID,
) -> Icon | None:
    stmt = select(Icon).where(Icon.account_id == account_id, Icon.id == icon_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_icon_by_slug(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    slug: str,
) -> Icon | None:
    stmt = select(Icon).where(Icon.account_id == account_id, Icon.slug == slug)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_icon(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: IconCreate,
) -> Icon:
    existing = await get_icon_by_slug(session, account_id=account_id, slug=payload.slug)
    if existing is not None:
        raise ValueError("Icon slug already exists for this account")
    icon = Icon(
        account_id=account_id,
        name=payload.name,
        slug=payload.slug,
        symbol=payload.symbol,
        color=payload.color,
        description=payload.description,
        applies_to=payload.applies_to,
        popup_text=payload.popup_text,
        affects_capacity=payload.affects_capacity,
    )
    session.add(icon)
    await session.commit()
    await session.refresh(icon)
    return icon


async def update_icon(
    session: AsyncSession,
    *,
    icon: Icon,
    payload: IconUpdate,
    account_id: uuid.UUID,
) -> Icon:
    updates = payload.model_dump(exclude_unset=True)
    if "slug" in updates and updates["slug"] != icon.slug:
        existing = await get_icon_by_slug(
            session, account_id=account_id, slug=updates["slug"]
        )
        if existing is not None:
            raise ValueError("Icon slug already exists for this account")
    for field, value in updates.items():
        setattr(icon, field, value)
    session.add(icon)
    await session.commit()
    await session.refresh(icon)
    return icon


async def delete_icon(session: AsyncSession, *, icon: Icon) -> None:
    await session.delete(icon)
    await session.commit()


async def list_owner_assignments(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
) -> Sequence[OwnerIcon]:
    stmt = (
        select(OwnerIcon)
        .options(selectinload(OwnerIcon.icon))
        .where(OwnerIcon.account_id == account_id)
    )
    if owner_id is not None:
        stmt = stmt.where(OwnerIcon.owner_id == owner_id)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def list_pet_assignments(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID | None = None,
) -> Sequence[PetIcon]:
    stmt = (
        select(PetIcon)
        .options(selectinload(PetIcon.icon))
        .where(PetIcon.account_id == account_id)
    )
    if pet_id is not None:
        stmt = stmt.where(PetIcon.pet_id == pet_id)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def assign_icon_to_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: OwnerIconAssignmentCreate,
) -> OwnerIcon:
    owner = await session.get(
        OwnerProfile,
        payload.owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Owner not found for account")

    icon = await get_icon(session, account_id=account_id, icon_id=payload.icon_id)
    if icon is None:
        raise ValueError("Icon not found for account")

    assignment = OwnerIcon(
        account_id=account_id,
        owner_id=payload.owner_id,
        icon_id=payload.icon_id,
        notes=payload.notes,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    await session.refresh(assignment, attribute_names=["icon"])
    return assignment


async def remove_owner_icon(session: AsyncSession, *, assignment: OwnerIcon) -> None:
    await session.delete(assignment)
    await session.commit()


async def assign_icon_to_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: PetIconAssignmentCreate,
) -> PetIcon:
    pet = await session.get(
        Pet,
        payload.pet_id,
        options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
    )
    if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Pet not found for account")

    icon = await get_icon(session, account_id=account_id, icon_id=payload.icon_id)
    if icon is None:
        raise ValueError("Icon not found for account")

    assignment = PetIcon(
        account_id=account_id,
        pet_id=payload.pet_id,
        icon_id=payload.icon_id,
        notes=payload.notes,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    await session.refresh(assignment, attribute_names=["icon"])
    return assignment


async def remove_pet_icon(session: AsyncSession, *, assignment: PetIcon) -> None:
    await session.delete(assignment)
    await session.commit()


async def get_owner_icon_assignment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    assignment_id: uuid.UUID,
) -> OwnerIcon | None:
    stmt = select(OwnerIcon).where(
        OwnerIcon.account_id == account_id,
        OwnerIcon.id == assignment_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_pet_icon_assignment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    assignment_id: uuid.UUID,
) -> PetIcon | None:
    stmt = select(PetIcon).where(
        PetIcon.account_id == account_id,
        PetIcon.id == assignment_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
