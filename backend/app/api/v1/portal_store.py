"""Owner portal store endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.api.v1.portal import _ensure_portal_owner
from app.integrations import StripeClient, StripeClientError
from app.models import PackageType
from app.models.user import User, UserRole
from app.schemas.store import (
    PackageBalanceRead,
    PortalGiftCertificatePurchaseRequest,
    PortalGiftCertificateRedeemRequest,
    PortalPackagePurchaseRequest,
    PortalPurchaseResponse,
    PortalStoreBalancesResponse,
    PortalStoreCreditApplyRequest,
    StoreCreditSummary,
)
from app.services import (
    gift_cert_service,
    packages_service,
    payments_service,
    store_credit_service,
)

router = APIRouter(prefix="/portal", tags=["portal-store"])


@router.get("/store/package-types", response_model=list[PackageBalanceRead])
async def list_portal_packages(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[PackageBalanceRead]:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)
    stmt = (
        select(PackageType)
        .where(
            PackageType.account_id == current_user.account_id,
            PackageType.active.is_(True),
        )
        .order_by(PackageType.created_at.asc())
    )
    packages = (await session.execute(stmt)).scalars().all()
    response: list[PackageBalanceRead] = []
    for package in packages:
        response.append(
            PackageBalanceRead(
                package_type_id=package.id,
                name=package.name,
                applies_to=package.applies_to.value,
                remaining=0,
            )
        )
    # Merge remaining balances for owner
    balances: list[dict[str, Any]] = await packages_service.remaining_credits(
        session,
        owner_id=owner.id,
        account_id=current_user.account_id,
    )
    remaining_lookup = {entry["package_type_id"]: entry for entry in balances}
    for item in response:
        entry = remaining_lookup.get(item.package_type_id)
        if entry is not None:
            item.remaining = int(entry["remaining"])
    return response


@router.get("/store/balances", response_model=PortalStoreBalancesResponse)
async def get_store_balances(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PortalStoreBalancesResponse:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)

    package_entries: list[dict[str, Any]] = await packages_service.remaining_credits(
        session,
        owner_id=owner.id,
        account_id=current_user.account_id,
    )
    package_models = [
        PackageBalanceRead(
            package_type_id=entry["package_type_id"],
            name=str(entry["name"]),
            applies_to=str(entry["applies_to"]),
            remaining=int(entry["remaining"]),
        )
        for entry in package_entries
    ]
    balance = await store_credit_service.owner_balance(
        session,
        account_id=current_user.account_id,
        owner_id=owner.id,
    )
    return PortalStoreBalancesResponse(
        packages=package_models,
        store_credit=StoreCreditSummary(balance=balance),
    )


@router.post(
    "/store/packages/buy",
    response_model=PortalPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def buy_package(
    payload: PortalPackagePurchaseRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PortalPurchaseResponse:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)

    invoice_id = await packages_service.purchase_package(
        session,
        owner_id=owner.id,
        package_type_id=payload.package_type_id,
        quantity=payload.quantity,
    )

    try:
        (
            client_secret,
            transaction_id,
        ) = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=current_user.account_id,
            invoice_id=invoice_id,
            stripe=stripe_client,
        )
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PortalPurchaseResponse(
        invoice_id=invoice_id,
        client_secret=client_secret,
        transaction_id=transaction_id,
    )


@router.post(
    "/store/gift-certificates/buy",
    response_model=PortalPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def buy_gift_certificate(
    payload: PortalGiftCertificatePurchaseRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PortalPurchaseResponse:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)

    invoice_id, certificate = await gift_cert_service.purchase_gift_certificate(
        session,
        account_id=current_user.account_id,
        purchaser_owner_id=owner.id,
        amount=payload.amount,
        recipient_owner_id=owner.id,
        recipient_email=payload.recipient_email,
    )

    try:
        (
            client_secret,
            transaction_id,
        ) = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=current_user.account_id,
            invoice_id=invoice_id,
            stripe=stripe_client,
        )
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PortalPurchaseResponse(
        invoice_id=invoice_id,
        client_secret=client_secret,
        transaction_id=transaction_id,
        gift_certificate_id=certificate.id,
        gift_certificate_code=certificate.code,
    )


@router.post(
    "/store/gift-certificates/redeem", response_model=PortalStoreBalancesResponse
)
async def redeem_gift_certificate(
    payload: PortalGiftCertificateRedeemRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PortalStoreBalancesResponse:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)

    await gift_cert_service.redeem_gift_certificate(
        session,
        code=payload.code,
        account_id=current_user.account_id,
        owner_id=owner.id,
    )
    return await get_store_balances(session, current_user)


@router.post(
    "/invoices/{invoice_id}/apply-store-credit",
    response_model=PortalStoreBalancesResponse,
)
async def apply_store_credit(
    invoice_id: uuid.UUID,
    payload: PortalStoreCreditApplyRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PortalStoreBalancesResponse:
    if current_user.role != UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners only")
    owner = await _ensure_portal_owner(session, current_user)

    try:
        await store_credit_service.apply_store_credit(
            session,
            invoice_id=invoice_id,
            account_id=current_user.account_id,
            owner_id=owner.id,
            amount=payload.amount,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return await get_store_balances(session, current_user)
