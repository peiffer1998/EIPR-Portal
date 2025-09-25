"""Agreement template and signature endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas import (
    AgreementSignatureCreate,
    AgreementSignatureRead,
    AgreementTemplateCreate,
    AgreementTemplateRead,
    AgreementTemplateUpdate,
)
from app.services import agreement_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "/templates",
    response_model=list[AgreementTemplateRead],
    summary="List agreement templates",
)
async def list_templates(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    include_inactive: bool = Query(default=True),
) -> list[AgreementTemplateRead]:
    _assert_staff(current_user)
    templates = await agreement_service.list_templates(
        session,
        account_id=current_user.account_id,
        include_inactive=include_inactive,
    )
    return [AgreementTemplateRead.model_validate(item) for item in templates]


@router.post(
    "/templates",
    response_model=AgreementTemplateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create agreement template",
)
async def create_template(
    payload: AgreementTemplateCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AgreementTemplateRead:
    _assert_staff(current_user)
    template = await agreement_service.create_template(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return AgreementTemplateRead.model_validate(template)


@router.patch(
    "/templates/{template_id}",
    response_model=AgreementTemplateRead,
    summary="Update agreement template",
)
async def update_template(
    template_id: uuid.UUID,
    payload: AgreementTemplateUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AgreementTemplateRead:
    _assert_staff(current_user)
    template = await agreement_service.get_template(
        session,
        account_id=current_user.account_id,
        template_id=template_id,
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agreement template not found"
        )
    updated = await agreement_service.update_template(
        session,
        template=template,
        payload=payload,
    )
    return AgreementTemplateRead.model_validate(updated)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agreement template",
)
async def delete_template(
    template_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    template = await agreement_service.get_template(
        session,
        account_id=current_user.account_id,
        template_id=template_id,
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agreement template not found"
        )
    await agreement_service.delete_template(session, template=template)
    return None


@router.get(
    "/signatures",
    response_model=list[AgreementSignatureRead],
    summary="List agreement signatures",
)
async def list_signatures(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    template_id: uuid.UUID | None = Query(default=None),
) -> list[AgreementSignatureRead]:
    if current_user.role != UserRole.PET_PARENT:
        # staff can see all signatures
        signatures = await agreement_service.list_signatures(
            session,
            account_id=current_user.account_id,
            template_id=template_id,
        )
    else:
        owner = await deps.get_current_owner_profile(session, current_user)
        signatures = await agreement_service.list_signatures(
            session,
            account_id=current_user.account_id,
            template_id=template_id,
        )
        signatures = [
            sig
            for sig in signatures
            if sig.owner_id == getattr(owner, "id", None)
            or sig.pet_id in {pet.id for pet in getattr(owner, "pets", [])}
        ]
    return [AgreementSignatureRead.model_validate(item) for item in signatures]


@router.post(
    "/signatures",
    response_model=AgreementSignatureRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record agreement signature",
)
async def create_signature(
    payload: AgreementSignatureCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AgreementSignatureRead:
    if current_user.role == UserRole.PET_PARENT:
        owner = await deps.get_current_owner_profile(session, current_user)
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Owner profile not found"
            )
        if payload.owner_id is None:
            payload = payload.model_copy(update={"owner_id": owner.id})
    else:
        _assert_staff(current_user)
    signature = await agreement_service.record_signature(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return AgreementSignatureRead.model_validate(signature)
