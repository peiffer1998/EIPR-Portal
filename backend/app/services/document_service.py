"""Services for document metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.schemas.document import DocumentCreate


async def list_documents(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
    pet_id: uuid.UUID | None = None,
) -> list[Document]:
    stmt: Select[tuple[Document]] = select(Document).where(
        Document.account_id == account_id
    )
    if owner_id is not None:
        stmt = stmt.where(Document.owner_id == owner_id)
    if pet_id is not None:
        stmt = stmt.where(Document.pet_id == pet_id)
    stmt = stmt.options(selectinload(Document.owner), selectinload(Document.pet))
    result = await session.execute(stmt.order_by(Document.created_at.desc()))
    return list(result.scalars().unique().all())


async def get_document(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document | None:
    stmt = select(Document).where(
        Document.id == document_id, Document.account_id == account_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_document(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID | None,
    payload: DocumentCreate,
) -> Document:
    if payload.owner_id is not None:
        owner = await session.get(
            OwnerProfile,
            payload.owner_id,
            options=[selectinload(OwnerProfile.user)],
        )
        if owner is None or owner.user.account_id != account_id:  # type: ignore[union-attr]
            raise ValueError("Owner not found for account")
    if payload.pet_id is not None:
        pet = await session.get(
            Pet,
            payload.pet_id,
            options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
        )
        if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
            raise ValueError("Pet not found for account")

    document = Document(
        account_id=account_id,
        owner_id=payload.owner_id,
        pet_id=payload.pet_id,
        uploaded_by_user_id=uploaded_by_user_id,
        file_name=payload.file_name,
        content_type=payload.content_type,
        object_key=payload.object_key,
        url=payload.url,
        notes=payload.notes,
        sha256=payload.sha256,
        object_key_web=payload.object_key_web,
        bytes_web=payload.bytes_web,
        width=payload.width,
        height=payload.height,
        content_type_web=payload.content_type_web
        or ("image/webp" if payload.object_key_web else None),
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def delete_document(session: AsyncSession, *, document: Document) -> None:
    await session.delete(document)
    await session.commit()
