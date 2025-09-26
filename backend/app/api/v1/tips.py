"""Tip management endpoints."""

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import TipShare, TipTransaction, User, UserRole
from app.schemas.payroll import TipCreate, TipRead, TipShareRead
from app.services import tip_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post(
    "/tips",
    response_model=TipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record tip",
)
async def create_tip(
    payload: TipCreate,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> TipRead:
    _assert_staff(current_user)
    try:
        tx = await tip_service.record_tip(
            session,
            account_id=current_user.account_id,
            location_id=payload.location_id,
            d=payload.date,
            amount=payload.amount,
            policy=payload.policy,
            recipients=payload.recipients,
            appointment_id=payload.appointment_id,
            payment_transaction_id=payload.payment_transaction_id,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    shares = (
        (
            await session.execute(
                select(TipShare).where(TipShare.tip_transaction_id == tx.id)
            )
        )
        .scalars()
        .all()
    )
    return TipRead(
        id=tx.id,
        account_id=tx.account_id,
        location_id=tx.location_id,
        date=tx.date,
        amount=tx.amount,
        policy=tx.policy,
        shares=[
            TipShareRead(user_id=s.user_id, amount=s.amount, method=s.method)
            for s in shares
        ],
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


@router.get("/tips", response_model=list[TipRead], summary="List tips")
async def list_tips(
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> list[TipRead]:
    _assert_staff(current_user)
    txs = (
        (
            await session.execute(
                select(TipTransaction).where(
                    TipTransaction.account_id == current_user.account_id
                )
            )
        )
        .scalars()
        .all()
    )
    result: list[TipRead] = []
    for tx in txs:
        shares = (
            (
                await session.execute(
                    select(TipShare).where(TipShare.tip_transaction_id == tx.id)
                )
            )
            .scalars()
            .all()
        )
        result.append(
            TipRead(
                id=tx.id,
                account_id=tx.account_id,
                location_id=tx.location_id,
                date=tx.date,
                amount=tx.amount,
                policy=tx.policy,
                shares=[
                    TipShareRead(user_id=s.user_id, amount=s.amount, method=s.method)
                    for s in shares
                ],
                created_at=tx.created_at,
                updated_at=tx.updated_at,
            )
        )
    return result
