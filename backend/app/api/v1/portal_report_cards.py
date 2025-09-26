"""Owner-facing report card endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import S3Client
from app.models import User, UserRole
from app.schemas.report_card import ReportCardRead
from app.services import owner_service, report_card_service

router = APIRouter()


def _optional_s3_client() -> S3Client | None:
    try:
        return deps.get_s3_client()
    except HTTPException:  # pragma: no cover
        return None


def _require_pet_parent(user: User) -> None:
    if user.role != UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access is limited to pet parents",
        )


@router.get(
    "/report-cards", response_model=list[ReportCardRead], summary="List my report cards"
)
async def list_my_report_cards(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    pet_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[ReportCardRead]:
    _require_pet_parent(current_user)
    owner = await owner_service.get_owner_by_user(session, user_id=current_user.id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Owner profile not found")

    return await report_card_service.list_cards(
        session,
        account_id=current_user.account_id,
        owner_id=owner.id,
        pet_id=pet_id,
        s3_client=_optional_s3_client(),
    )


@router.get(
    "/report-cards/{card_id}",
    response_model=ReportCardRead,
    summary="View report card",
)
async def get_my_report_card(
    card_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _require_pet_parent(current_user)
    owner = await owner_service.get_owner_by_user(session, user_id=current_user.id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Owner profile not found")
    try:
        card = await report_card_service.get_card(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            s3_client=_optional_s3_client(),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if card.owner_id != owner.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report card not found")
    return card
