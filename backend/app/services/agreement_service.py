"""Service helpers for agreement templates and signatures."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agreement import AgreementSignature, AgreementTemplate
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.user import User
from app.schemas.agreement import (
    AgreementSignatureCreate,
    AgreementTemplateCreate,
    AgreementTemplateUpdate,
)


async def list_templates(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    include_inactive: bool = True,
) -> Sequence[AgreementTemplate]:
    stmt: Select[tuple[AgreementTemplate]] = select(AgreementTemplate).where(
        AgreementTemplate.account_id == account_id
    )
    if not include_inactive:
        stmt = stmt.where(AgreementTemplate.is_active.is_(True))
    stmt = stmt.order_by(AgreementTemplate.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_template(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    template_id: uuid.UUID,
) -> AgreementTemplate | None:
    stmt = select(AgreementTemplate).where(
        AgreementTemplate.account_id == account_id,
        AgreementTemplate.id == template_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_template(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: AgreementTemplateCreate,
) -> AgreementTemplate:
    template = AgreementTemplate(
        account_id=account_id,
        title=payload.title,
        body=payload.body,
        requires_signature=payload.requires_signature,
        is_active=payload.is_active,
        version=payload.version,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def update_template(
    session: AsyncSession,
    *,
    template: AgreementTemplate,
    payload: AgreementTemplateUpdate,
) -> AgreementTemplate:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def delete_template(
    session: AsyncSession,
    *,
    template: AgreementTemplate,
) -> None:
    await session.delete(template)
    await session.commit()


async def list_signatures(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    template_id: uuid.UUID | None = None,
) -> Sequence[AgreementSignature]:
    stmt = (
        select(AgreementSignature)
        .join(AgreementTemplate)
        .options(
            selectinload(AgreementSignature.owner).selectinload(OwnerProfile.user),
            selectinload(AgreementSignature.pet),
            selectinload(AgreementSignature.signed_by_user),
        )
        .where(AgreementTemplate.account_id == account_id)
        .order_by(AgreementSignature.signed_at.desc())
    )
    if template_id is not None:
        stmt = stmt.where(AgreementSignature.agreement_template_id == template_id)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def record_signature(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: AgreementSignatureCreate,
) -> AgreementSignature:
    template = await get_template(
        session, account_id=account_id, template_id=payload.agreement_template_id
    )
    if template is None:
        raise ValueError("Agreement template not found for account")

    owner: OwnerProfile | None = None
    if payload.owner_id is not None:
        owner = await session.get(
            OwnerProfile,
            payload.owner_id,
            options=[selectinload(OwnerProfile.user)],
        )
        if owner is None or owner.user.account_id != account_id:  # type: ignore[union-attr]
            raise ValueError("Owner not found for account")

    pet: Pet | None = None
    if payload.pet_id is not None:
        pet = await session.get(
            Pet,
            payload.pet_id,
            options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
        )
        if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
            raise ValueError("Pet not found for account")

    signed_by_user: User | None = None
    if payload.signed_by_user_id is not None:
        signed_by_user = await session.get(User, payload.signed_by_user_id)
        if signed_by_user is None or signed_by_user.account_id != account_id:
            raise ValueError("User not found for account")

    signature = AgreementSignature(
        agreement=template,
        owner=owner,
        pet=pet,
        signed_by_user=signed_by_user,
        ip_address=payload.ip_address,
        notes=payload.notes,
    )
    session.add(signature)
    await session.commit()
    await session.refresh(signature)
    return signature
