"""Operations for the service catalog."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_catalog_item import ServiceCatalogItem, ServiceCatalogKind
from app.schemas.service_catalog import ServiceCatalogItemCreate, ServiceCatalogItemUpdate


async def list_items(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    kind: ServiceCatalogKind | None = None,
) -> list[ServiceCatalogItem]:
    stmt: Select[tuple[ServiceCatalogItem]] = select(ServiceCatalogItem).where(
        ServiceCatalogItem.account_id == account_id
    )
    if kind is not None:
        stmt = stmt.where(ServiceCatalogItem.kind == kind)
    stmt = stmt.order_by(ServiceCatalogItem.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_item(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    item_id: uuid.UUID,
) -> ServiceCatalogItem | None:
    stmt = select(ServiceCatalogItem).where(
        ServiceCatalogItem.id == item_id,
        ServiceCatalogItem.account_id == account_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_item(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: ServiceCatalogItemCreate,
) -> ServiceCatalogItem:
    item = ServiceCatalogItem(
        account_id=account_id,
        name=payload.name,
        description=payload.description,
        kind=payload.kind,
        reservation_type=payload.reservation_type,
        duration_minutes=payload.duration_minutes,
        base_price=Decimal(str(payload.base_price)) if payload.base_price is not None else None,
        active=payload.active,
        sku=payload.sku,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_item(
    session: AsyncSession,
    *,
    item: ServiceCatalogItem,
    payload: ServiceCatalogItemUpdate,
) -> ServiceCatalogItem:
    data = payload.model_dump(exclude_unset=True)
    if "base_price" in data and data["base_price"] is not None:
        data["base_price"] = Decimal(str(data["base_price"]))
    for key, value in data.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_item(session: AsyncSession, *, item: ServiceCatalogItem) -> None:
    await session.delete(item)
    await session.commit()
