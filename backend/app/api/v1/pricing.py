"""Pricing-related API endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.pricing import PricingQuoteRead, PricingQuoteRequest
from app.services import pricing_service, reservation_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


async def _assert_quote_permissions(
    session: AsyncSession,
    *,
    reservation_id: UUID,
    current_user: User,
) -> None:
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    if current_user.role == UserRole.PET_PARENT:
        owner = reservation.pet.owner if reservation.pet else None
        if owner is None or owner.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )


@router.post(
    "/quote", response_model=PricingQuoteRead, summary="Quote reservation pricing"
)
async def quote_reservation_pricing(
    payload: PricingQuoteRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PricingQuoteRead:
    await _assert_quote_permissions(
        session,
        reservation_id=payload.reservation_id,
        current_user=current_user,
    )
    try:
        quote = await pricing_service.quote_reservation(
            session,
            reservation_id=payload.reservation_id,
            account_id=current_user.account_id,
            promotion_code=payload.promotion_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return PricingQuoteRead.model_validate(quote)
