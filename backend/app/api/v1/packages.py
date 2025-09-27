"""Service package endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.package import (
    ServicePackageCreate,
    ServicePackageRead,
    ServicePackageUpdate,
)
from app.services import package_service

router = APIRouter(prefix="/packages")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get("", response_model=list[ServicePackageRead], summary="List packages")
async def list_packages(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[ServicePackageRead]:
    _assert_staff(current_user)
    packages = await package_service.list_packages(
        session, account_id=current_user.account_id
    )
    return [ServicePackageRead.model_validate(pkg) for pkg in packages]


@router.post(
    "",
    response_model=ServicePackageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create package",
)
async def create_package(
    payload: ServicePackageCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ServicePackageRead:
    _assert_staff(current_user)
    package = await package_service.create_package(
        session,
        account_id=current_user.account_id,
        payload=payload,
    )
    return ServicePackageRead.model_validate(package)


@router.patch(
    "/{package_id}", response_model=ServicePackageRead, summary="Update package"
)
async def update_package(
    package_id: uuid.UUID,
    payload: ServicePackageUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ServicePackageRead:
    _assert_staff(current_user)
    package = await package_service.get_package(
        session,
        account_id=current_user.account_id,
        package_id=package_id,
    )
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    updated = await package_service.update_package(
        session, package=package, payload=payload
    )
    return ServicePackageRead.model_validate(updated)


@router.delete(
    "/{package_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete package"
)
async def delete_package(
    package_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    package = await package_service.get_package(
        session,
        account_id=current_user.account_id,
        package_id=package_id,
    )
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    await package_service.delete_package(session, package=package)
    return None
