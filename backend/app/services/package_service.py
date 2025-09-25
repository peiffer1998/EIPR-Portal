"""Service package management."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_package import ServicePackage
from app.schemas.package import ServicePackageCreate, ServicePackageUpdate


async def list_packages(session: AsyncSession, *, account_id: uuid.UUID) -> list[ServicePackage]:
    stmt: Select[tuple[ServicePackage]] = select(ServicePackage).where(
        ServicePackage.account_id == account_id
    ).order_by(ServicePackage.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_package(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    package_id: uuid.UUID,
) -> ServicePackage | None:
    stmt = select(ServicePackage).where(
        ServicePackage.id == package_id,
        ServicePackage.account_id == account_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_package(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: ServicePackageCreate,
) -> ServicePackage:
    package = ServicePackage(
        account_id=account_id,
        name=payload.name,
        description=payload.description,
        reservation_type=payload.reservation_type,
        credit_quantity=payload.credit_quantity,
        price=Decimal(str(payload.price)),
        active=payload.active,
    )
    session.add(package)
    await session.commit()
    await session.refresh(package)
    return package


async def update_package(
    session: AsyncSession,
    *,
    package: ServicePackage,
    payload: ServicePackageUpdate,
) -> ServicePackage:
    data = payload.model_dump(exclude_unset=True)
    if "price" in data and data["price"] is not None:
        data["price"] = Decimal(str(data["price"]))
    for key, value in data.items():
        setattr(package, key, value)
    await session.commit()
    await session.refresh(package)
    return package


async def delete_package(session: AsyncSession, *, package: ServicePackage) -> None:
    await session.delete(package)
    await session.commit()
