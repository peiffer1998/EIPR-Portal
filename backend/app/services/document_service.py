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
from app.integrations import S3Client
from app.services.image_service import hash_bytes, to_webp
from app.core.config import Settings


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


async def finalize_document_from_storage(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    pet_id: uuid.UUID | None,
    object_key: str,
    file_name: str,
    content_type: str,
    notes: str | None,
    s3_client: S3Client,
    settings: Settings,
) -> tuple[Document, str]:
    """Create a document record from an object stored in S3-compatible storage."""

    content_type_value = content_type or "application/octet-stream"

    original_bytes = s3_client.get_object_bytes(object_key)
    sha_hex = hash_bytes(original_bytes)

    reuse_web: Document | None = None
    if settings.image_dedup:
        result = await session.execute(
            select(Document)
            .where(
                Document.account_id == account_id,
                Document.sha256 == sha_hex,
                Document.object_key_web.is_not(None),
            )
            .limit(1)
        )
        reuse_web = result.scalar_one_or_none()

    object_key_web: str | None = None
    bytes_web: int | None = None
    width: int | None = None
    height: int | None = None
    content_type_web: str | None = None

    if reuse_web is not None and reuse_web.object_key_web:
        object_key_web = reuse_web.object_key_web
        bytes_web = reuse_web.bytes_web
        width = reuse_web.width
        height = reuse_web.height
        content_type_web = reuse_web.content_type_web or "image/webp"
    elif content_type_value.lower().startswith("image/"):
        web_bytes, width, height = to_webp(
            original_bytes,
            settings.image_max_width,
            settings.image_webp_quality,
        )
        if width and height and web_bytes:
            object_key_web = f"web/{account_id}/{sha_hex}.webp"
            s3_client.put_object_with_cache(
                object_key_web,
                web_bytes,
                content_type="image/webp",
                cache_seconds=settings.s3_cache_seconds,
                tags={"class": "web", "keep": "true"},
            )
            bytes_web = len(web_bytes)
            content_type_web = "image/webp"

    if settings.image_keep_original_days > 0:
        try:
            s3_client.put_object_tagging(
                object_key,
                {"class": "orig", "retain": str(settings.image_keep_original_days)},
            )
        except Exception:  # pragma: no cover - best effort only
            pass

    url = s3_client.build_object_url(object_key)
    url_web = (
        s3_client.build_object_url(object_key_web)
        if object_key_web is not None
        else None
    )

    document = await create_document(
        session,
        account_id=account_id,
        uploaded_by_user_id=uploaded_by_user_id,
        payload=DocumentCreate(
            file_name=file_name,
            content_type=content_type_value,
            object_key=object_key,
            url=url,
            owner_id=owner_id,
            pet_id=pet_id,
            notes=notes,
            sha256=sha_hex,
            object_key_web=object_key_web,
            bytes_web=bytes_web,
            width=width,
            height=height,
            content_type_web=content_type_web,
            url_web=url_web,
        ),
    )
    return document, sha_hex
