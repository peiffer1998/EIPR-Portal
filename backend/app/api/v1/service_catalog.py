"""Service catalog endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.service_catalog_item import ServiceCatalogKind
from app.models.user import User, UserRole
from app.schemas.service_catalog import (
    ServiceCatalogItemCreate,
    ServiceCatalogItemRead,
    ServiceCatalogItemUpdate,
)
from app.services import service_catalog_service

router = APIRouter(prefix="/service-items")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "", response_model=list[ServiceCatalogItemRead], summary="List catalog items"
)
async def list_catalog_items(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    kind: ServiceCatalogKind | None = Query(default=None),
) -> list[ServiceCatalogItemRead]:
    _assert_staff(current_user)
    items = await service_catalog_service.list_items(
        session,
        account_id=current_user.account_id,
        kind=kind,
    )
    return [ServiceCatalogItemRead.model_validate(item) for item in items]


@router.post(
    "",
    response_model=ServiceCatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create catalog item",
)
async def create_catalog_item(
    payload: ServiceCatalogItemCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ServiceCatalogItemRead:
    _assert_staff(current_user)
    if payload.kind == ServiceCatalogKind.SERVICE and payload.reservation_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reservation_type required for services",
        )
    try:
        item = await service_catalog_service.create_item(
            session,
            account_id=current_user.account_id,
            payload=payload,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate SKU"
        ) from exc
    return ServiceCatalogItemRead.model_validate(item)


@router.get(
    "/{item_id}", response_model=ServiceCatalogItemRead, summary="Get catalog item"
)
async def get_catalog_item(
    item_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ServiceCatalogItemRead:
    _assert_staff(current_user)
    item = await service_catalog_service.get_item(
        session,
        account_id=current_user.account_id,
        item_id=item_id,
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return ServiceCatalogItemRead.model_validate(item)


@router.patch(
    "/{item_id}", response_model=ServiceCatalogItemRead, summary="Update catalog item"
)
async def update_catalog_item(
    item_id: uuid.UUID,
    payload: ServiceCatalogItemUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ServiceCatalogItemRead:
    _assert_staff(current_user)
    item = await service_catalog_service.get_item(
        session,
        account_id=current_user.account_id,
        item_id=item_id,
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    try:
        updated = await service_catalog_service.update_item(
            session, item=item, payload=payload
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate SKU"
        ) from exc
    return ServiceCatalogItemRead.model_validate(updated)


@router.delete(
    "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete catalog item"
)
async def delete_catalog_item(
    item_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    item = await service_catalog_service.get_item(
        session,
        account_id=current_user.account_id,
        item_id=item_id,
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    await service_catalog_service.delete_item(session, item=item)
    return None
