"""Document metadata endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate, DocumentRead
from app.services import document_service

router = APIRouter(prefix="/documents")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


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
    return [DocumentRead.model_validate(doc) for doc in docs]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED, summary="Create document metadata")
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete document")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await document_service.delete_document(session, document=document)
    return None
