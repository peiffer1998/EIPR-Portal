"""Staff store management endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models import (
    GiftCertificate,
    Invoice,
    PackageType,
    Pet,
    Reservation,
    StoreCreditSource,
)
from app.models.user import User, UserRole
from app.schemas.store import (
    GiftCertificateIssueRequest,
    GiftCertificateRead,
    GiftCertificateRedeemRequest,
    PackageCreditApplicationRead,
    PackagePurchaseRequest,
    PackagePurchaseResponse,
    PackageTypeCreate,
    PackageTypeRead,
    PackageTypeUpdate,
    StoreCreditAddRequest,
    StoreCreditApplyRequest,
    StoreCreditBalanceResponse,
)
from app.services import (
    gift_cert_service,
    packages_service,
    store_credit_service,
)

router = APIRouter(prefix="/store", tags=["store"])


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


async def _get_package_type(
    session: AsyncSession,
    *,
    package_type_id: uuid.UUID,
    account_id: uuid.UUID,
) -> PackageType:
    package = await session.get(PackageType, package_type_id)
    if package is None or package.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package type not found"
        )
    return package


async def _get_invoice_owner_id(
    session: AsyncSession,
    *,
    invoice_id: uuid.UUID,
    account_id: uuid.UUID,
) -> uuid.UUID:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
        .options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner),
        )
    )
    invoice = (await session.execute(stmt)).scalars().unique().one_or_none()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    reservation = invoice.reservation
    owner = getattr(getattr(reservation, "pet", None), "owner", None)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice reservation is missing owner information",
        )
    return owner.id


@router.post(
    "/package-types",
    response_model=PackageTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a package type",
)
async def create_package_type(
    payload: PackageTypeCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PackageTypeRead:
    _require_staff(current_user)
    package = PackageType(
        account_id=current_user.account_id,
        name=payload.name,
        applies_to=payload.applies_to,
        credits_per_package=payload.credits_per_package,
        price=payload.price,
        active=payload.active,
    )
    session.add(package)
    await session.commit()
    await session.refresh(package)
    return PackageTypeRead.model_validate(package)


@router.get(
    "/package-types",
    response_model=list[PackageTypeRead],
    summary="List package types",
)
async def list_package_types(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    active: bool | None = Query(default=None),
) -> list[PackageTypeRead]:
    _require_staff(current_user)
    stmt = select(PackageType).where(PackageType.account_id == current_user.account_id)
    if active is not None:
        stmt = stmt.where(PackageType.active == active)
    packages = (
        (await session.execute(stmt.order_by(PackageType.created_at.desc())))
        .scalars()
        .all()
    )
    return [PackageTypeRead.model_validate(pkg) for pkg in packages]


@router.patch(
    "/package-types/{package_type_id}",
    response_model=PackageTypeRead,
    summary="Update a package type",
)
async def update_package_type(
    package_type_id: uuid.UUID,
    payload: PackageTypeUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PackageTypeRead:
    _require_staff(current_user)
    package = await _get_package_type(
        session,
        package_type_id=package_type_id,
        account_id=current_user.account_id,
    )
    if payload.name is not None:
        package.name = payload.name
    if payload.applies_to is not None:
        package.applies_to = payload.applies_to
    if payload.credits_per_package is not None:
        package.credits_per_package = payload.credits_per_package
    if payload.price is not None:
        package.price = payload.price
    if payload.active is not None:
        package.active = payload.active
    await session.commit()
    await session.refresh(package)
    return PackageTypeRead.model_validate(package)


@router.delete(
    "/package-types/{package_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a package type",
)
async def delete_package_type(
    package_type_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _require_staff(current_user)
    package = await _get_package_type(
        session,
        package_type_id=package_type_id,
        account_id=current_user.account_id,
    )
    await session.delete(package)
    await session.commit()


@router.post(
    "/packages/purchase",
    response_model=PackagePurchaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Purchase a package for an owner",
)
async def purchase_package(
    payload: PackagePurchaseRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PackagePurchaseResponse:
    _require_staff(current_user)
    invoice_id = await packages_service.purchase_package(
        session,
        owner_id=payload.owner_id,
        package_type_id=payload.package_type_id,
        quantity=payload.quantity,
    )
    return PackagePurchaseResponse(invoice_id=invoice_id)


@router.post(
    "/invoices/{invoice_id}/apply-package-credits",
    response_model=PackageCreditApplicationRead,
    summary="Apply available package credits to an invoice",
)
async def apply_package_credits(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PackageCreditApplicationRead:
    _require_staff(current_user)
    summary = await packages_service.apply_package_credits(
        session,
        invoice_id=invoice_id,
        account_id=current_user.account_id,
    )
    return PackageCreditApplicationRead(
        invoice_id=summary.invoice_id,
        applied_amount=summary.applied_amount,
        units_consumed={str(k): v for k, v in summary.units_consumed.items()},
    )


@router.post(
    "/gift-certificates/issue",
    response_model=GiftCertificateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a gift certificate",
)
async def issue_gift_certificate(
    payload: GiftCertificateIssueRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> GiftCertificateRead:
    _require_staff(current_user)
    certificate = await gift_cert_service.issue_gift_certificate(
        session,
        account_id=current_user.account_id,
        purchaser_owner_id=payload.purchaser_owner_id,
        amount=payload.amount,
        recipient_owner_id=payload.recipient_owner_id,
        recipient_email=payload.recipient_email,
        expires_on=payload.expires_on,
    )
    return GiftCertificateRead.model_validate(certificate)


@router.get(
    "/gift-certificates",
    response_model=list[GiftCertificateRead],
    summary="List gift certificates",
)
async def list_gift_certificates(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: uuid.UUID | None = Query(default=None),
) -> list[GiftCertificateRead]:
    _require_staff(current_user)
    stmt = select(GiftCertificate).where(
        GiftCertificate.account_id == current_user.account_id
    )
    if owner_id is not None:
        stmt = stmt.where(
            or_(
                GiftCertificate.purchaser_owner_id == owner_id,
                GiftCertificate.recipient_owner_id == owner_id,
            )
        )
    certificates = (
        (await session.execute(stmt.order_by(GiftCertificate.created_at.desc())))
        .scalars()
        .all()
    )
    return [GiftCertificateRead.model_validate(cert) for cert in certificates]


@router.post(
    "/gift-certificates/redeem",
    response_model=StoreCreditBalanceResponse,
    summary="Redeem a gift certificate into store credit",
)
async def redeem_gift_certificate(
    payload: GiftCertificateRedeemRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> StoreCreditBalanceResponse:
    _require_staff(current_user)
    await gift_cert_service.redeem_gift_certificate(
        session,
        code=payload.code,
        account_id=current_user.account_id,
        owner_id=payload.owner_id,
    )
    balance = await store_credit_service.owner_balance(
        session,
        account_id=current_user.account_id,
        owner_id=payload.owner_id,
    )
    return StoreCreditBalanceResponse(owner_id=payload.owner_id, balance=balance)


@router.post(
    "/credit/add",
    response_model=StoreCreditBalanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add manual store credit",
)
async def add_store_credit(
    payload: StoreCreditAddRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> StoreCreditBalanceResponse:
    _require_staff(current_user)
    await store_credit_service.add_credit(
        session,
        account_id=current_user.account_id,
        owner_id=payload.owner_id,
        amount=payload.amount,
        source=StoreCreditSource.MANUAL,
        note=payload.note,
    )
    balance = await store_credit_service.owner_balance(
        session,
        account_id=current_user.account_id,
        owner_id=payload.owner_id,
    )
    return StoreCreditBalanceResponse(owner_id=payload.owner_id, balance=balance)


@router.get(
    "/credit/balance",
    response_model=StoreCreditBalanceResponse,
    summary="Get store credit balance for an owner",
)
async def get_store_credit_balance(
    owner_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> StoreCreditBalanceResponse:
    _require_staff(current_user)
    balance = await store_credit_service.owner_balance(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    return StoreCreditBalanceResponse(owner_id=owner_id, balance=balance)


@router.post(
    "/invoices/{invoice_id}/apply-store-credit",
    response_model=StoreCreditBalanceResponse,
    summary="Apply store credit to an invoice",
)
async def apply_store_credit(
    invoice_id: uuid.UUID,
    payload: StoreCreditApplyRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> StoreCreditBalanceResponse:
    _require_staff(current_user)
    owner_id = await _get_invoice_owner_id(
        session,
        invoice_id=invoice_id,
        account_id=current_user.account_id,
    )
    await store_credit_service.apply_store_credit(
        session,
        invoice_id=invoice_id,
        account_id=current_user.account_id,
        owner_id=owner_id,
        amount=payload.amount,
    )
    balance = await store_credit_service.owner_balance(
        session,
        account_id=current_user.account_id,
        owner_id=owner_id,
    )
    return StoreCreditBalanceResponse(owner_id=owner_id, balance=balance)
