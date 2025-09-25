"""Location capacity management API."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.capacity import CapacityRuleCreate, CapacityRuleRead, CapacityRuleUpdate
from app.services import capacity_service

router = APIRouter()


def _assert_management_role(user: User) -> None:
    if user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get(
    "/locations/{location_id}",
    response_model=list[CapacityRuleRead],
    summary="List capacity rules for a location",
)
async def list_capacity_rules(
    location_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[CapacityRuleRead]:
    _assert_management_role(current_user)
    try:
        rules = await capacity_service.list_capacity_rules(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [CapacityRuleRead.model_validate(rule) for rule in rules]


@router.post(
    "",
    response_model=CapacityRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create capacity rule",
)
async def create_capacity_rule(
    payload: CapacityRuleCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> CapacityRuleRead:
    _assert_management_role(current_user)
    try:
        rule = await capacity_service.create_capacity_rule(
            session,
            account_id=current_user.account_id,
            location_id=payload.location_id,
            reservation_type=payload.reservation_type,
            max_active=payload.max_active,
            waitlist_limit=payload.waitlist_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule already exists") from exc
    return CapacityRuleRead.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=CapacityRuleRead,
    summary="Update capacity rule",
)
async def update_capacity_rule(
    rule_id: uuid.UUID,
    payload: CapacityRuleUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> CapacityRuleRead:
    _assert_management_role(current_user)
    rule = await capacity_service.get_capacity_rule(
        session,
        account_id=current_user.account_id,
        rule_id=rule_id,
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capacity rule not found")

    try:
        updated = await capacity_service.update_capacity_rule(
            session,
            rule=rule,
            account_id=current_user.account_id,
            max_active=payload.max_active,
            waitlist_limit=payload.waitlist_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CapacityRuleRead.model_validate(updated)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete capacity rule",
)
async def delete_capacity_rule(
    rule_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_management_role(current_user)
    rule = await capacity_service.get_capacity_rule(
        session,
        account_id=current_user.account_id,
        rule_id=rule_id,
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capacity rule not found")
    await capacity_service.delete_capacity_rule(
        session,
        rule=rule,
        account_id=current_user.account_id,
    )
