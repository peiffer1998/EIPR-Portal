"""Document metadata endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import get_settings
from app.integrations import S3Client, S3ClientError
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate, DocumentFinalizeRequest, DocumentRead
from app.services import document_service
from app.services.image_service import hash_bytes, to_webp

router = APIRouter(prefix="/documents")
settings = get_settings()


def _try_get_s3_client() -> S3Client | None:
    try:
        return deps.get_s3_client()
    except HTTPException:
        return None


def _document_to_read(
    document: Document, *, s3_client: S3Client | None = None
) -> DocumentRead:
    result = DocumentRead.model_validate(document)
    if s3_client:
        if document.object_key:
            result.url = s3_client.build_object_url(document.object_key)
        if document.object_key_web:
            result.url_web = s3_client.build_object_url(document.object_key_web)
    else:
        if not result.url and document.url:
            result.url = document.url
        if not result.url_web and document.object_key_web and document.url:
            result.url_web = document.url
    return result


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get("", response_model=list[DocumentRead], summary="List documents")
async def list_documents(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: uuid.UUID | None = Query(default=None),
    pet_id: uuid.UUID | None = Query(default=None),
) -> list[DocumentRead]:
    _assert_staff(current_user)
    docs = await document_service.list_documents(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
        pet_id=pet_id,
    )
    s3_client = _try_get_s3_client()
    return [_document_to_read(doc, s3_client=s3_client) for doc in docs]


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create document metadata",
)
async def create_document(
    payload: DocumentCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> DocumentRead:
    _assert_staff(current_user)
    try:
        document = await document_service.create_document(
            session,
            account_id=current_user.account_id,
            uploaded_by_user_id=current_user.id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    s3_client = _try_get_s3_client()
    return _document_to_read(document, s3_client=s3_client)


@router.post(
    "/finalize",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Finalize an uploaded document",
)
async def finalize_document(
    payload: DocumentFinalizeRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    s3_client: Annotated[S3Client, Depends(deps.get_s3_client)],
) -> DocumentRead:
    _assert_staff(current_user)
    try:
        original_bytes = s3_client.get_object_bytes(payload.upload_key)
    except S3ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    sha_hex = hash_bytes(original_bytes)
    reuse_web: Document | None = None
    if settings.image_dedup:
        result = await session.execute(
            select(Document)
            .where(
                Document.account_id == current_user.account_id,
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
    elif payload.content_type.lower().startswith("image/"):
        web_bytes, width, height = to_webp(
            original_bytes,
            settings.image_max_width,
            settings.image_webp_quality,
        )
        object_key_web = f"web/{current_user.account_id}/{sha_hex}.webp"
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
                payload.upload_key,
                {"class": "orig", "retain": str(settings.image_keep_original_days)},
            )
        except S3ClientError:  # pragma: no cover - best effort only
            pass

    url = payload.url or s3_client.build_object_url(payload.upload_key)
    url_web = s3_client.build_object_url(object_key_web) if object_key_web else None

    try:
        document = await document_service.create_document(
            session,
            account_id=current_user.account_id,
            uploaded_by_user_id=current_user.id,
            payload=DocumentCreate(
                file_name=payload.file_name,
                content_type=payload.content_type,
                object_key=payload.upload_key,
                url=url,
                owner_id=payload.owner_id,
                pet_id=payload.pet_id,
                notes=payload.notes,
                sha256=sha_hex,
                object_key_web=object_key_web,
                bytes_web=bytes_web,
                width=width,
                height=height,
                content_type_web=content_type_web,
                url_web=url_web,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    response = _document_to_read(document, s3_client=s3_client)
    if url_web:
        response.url_web = url_web
    response.sha256 = sha_hex
    return response


@router.delete(
    "/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete document"
)
async def delete_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    document = await document_service.get_document(
        session,
        account_id=current_user.account_id,
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    await document_service.delete_document(session, document=document)
    return None
