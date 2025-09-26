"""Staff-facing report card management API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, NoReturn

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import S3Client
from app.models import User, UserRole
from app.schemas.report_card import (
    ReportCardCreate,
    ReportCardFriendsUpdate,
    ReportCardMediaAttach,
    ReportCardRead,
    ReportCardUpdate,
)
from app.services import report_card_service

router = APIRouter()


def _ensure_staff(current_user: User) -> None:
    if current_user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _optional_s3_client() -> S3Client | None:
    try:
        return deps.get_s3_client()
    except HTTPException:  # pragma: no cover - S3 optional in dev
        return None


def _raise_from_value_error(error: ValueError) -> NoReturn:
    detail = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    if "not found" in detail.lower():
        status_code = status.HTTP_404_NOT_FOUND
    raise HTTPException(status_code=status_code, detail=detail) from error


@router.post(
    "",
    response_model=ReportCardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create report card",
)
async def create_report_card(
    payload: ReportCardCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    s3_client = _optional_s3_client()
    try:
        card = await report_card_service.create_card(
            session,
            account_id=current_user.account_id,
            owner_id=payload.owner_id,
            pet_id=payload.pet_id,
            created_by_user_id=current_user.id,
            occurred_on=payload.occurred_on,
            title=payload.title,
            summary=payload.summary,
            rating=payload.rating,
            reservation_id=payload.reservation_id,
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
    return await report_card_service.get_card(
        session,
        account_id=current_user.account_id,
        card_id=card.id,
        s3_client=s3_client,
    )


@router.get(
    "",
    response_model=list[ReportCardRead],
    summary="List report cards",
)
async def list_report_cards(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: Annotated[uuid.UUID | None, Query()] = None,
    pet_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[ReportCardRead]:
    _ensure_staff(current_user)
    return await report_card_service.list_cards(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
        pet_id=pet_id,
        date_from=date_from,
        date_to=date_to,
        s3_client=_optional_s3_client(),
    )


@router.get(
    "/{card_id}",
    response_model=ReportCardRead,
    summary="Retrieve report card",
)
async def get_report_card(
    card_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    s3_client = _optional_s3_client()
    try:
        return await report_card_service.get_card(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            s3_client=s3_client,
        )
    except ValueError as exc:
        _raise_from_value_error(exc)


@router.patch(
    "/{card_id}",
    response_model=ReportCardRead,
    summary="Update report card",
)
async def update_report_card(
    card_id: uuid.UUID,
    payload: ReportCardUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    updates = payload.model_dump(exclude_unset=True)
    s3_client = _optional_s3_client()
    unset = report_card_service.UNSET
    title_value = updates.get("title", unset)
    summary_value = updates.get("summary", unset)
    rating_value = updates.get("rating", unset)
    occurred_on_value = updates.get("occurred_on", unset)
    reservation_value = updates.get("reservation_id", unset)
    try:
        card = await report_card_service.update_card(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            title=title_value,
            summary=summary_value,
            rating=rating_value,
            occurred_on=occurred_on_value,
            reservation_id=reservation_value,
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
    return await report_card_service.get_card(
        session,
        account_id=current_user.account_id,
        card_id=card.id,
        s3_client=s3_client,
    )


@router.post(
    "/{card_id}/media",
    response_model=ReportCardRead,
    summary="Attach media to report card",
)
async def attach_report_card_media(
    card_id: uuid.UUID,
    payload: ReportCardMediaAttach,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    s3_client = _optional_s3_client()
    try:
        await report_card_service.attach_media(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            document_ids=list(payload.document_ids),
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
    return await report_card_service.get_card(
        session,
        account_id=current_user.account_id,
        card_id=card_id,
        s3_client=s3_client,
    )


@router.post(
    "/{card_id}/friends",
    response_model=ReportCardRead,
    summary="Set report card friends",
)
async def update_report_card_friends(
    card_id: uuid.UUID,
    payload: ReportCardFriendsUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    s3_client = _optional_s3_client()
    try:
        await report_card_service.set_friends(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            friend_pet_ids=list(payload.friend_pet_ids),
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
    return await report_card_service.get_card(
        session,
        account_id=current_user.account_id,
        card_id=card_id,
        s3_client=s3_client,
    )


@router.post(
    "/{card_id}/send",
    response_model=ReportCardRead,
    summary="Mark report card as sent",
)
async def send_report_card(
    card_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReportCardRead:
    _ensure_staff(current_user)
    s3_client = _optional_s3_client()
    try:
        await report_card_service.mark_sent(
            session,
            account_id=current_user.account_id,
            card_id=card_id,
            background_tasks=background_tasks,
            s3_client=s3_client,
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
    return await report_card_service.get_card(
        session,
        account_id=current_user.account_id,
        card_id=card_id,
        s3_client=s3_client,
    )
