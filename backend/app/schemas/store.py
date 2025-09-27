"""Schemas for store, packages, gift certificates, and credit operations."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from app.models.store import PackageApplicationType


class MembershipRead(BaseModel):
    id: uuid.UUID
    name: str
    billing_period: str | None = None
    price: Decimal | None = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MembershipEnrollRequest(BaseModel):
    owner_id: uuid.UUID
    membership_id: uuid.UUID
    start_date: date


class MembershipActionResponse(BaseModel):
    status: str


class PackageTypeBase(BaseModel):
    name: str
    applies_to: PackageApplicationType
    credits_per_package: int = Field(ge=1)
    price: Decimal = Field(ge=Decimal("0"))
    active: bool = True


class PackageTypeCreate(PackageTypeBase):
    pass


class PackageTypeUpdate(BaseModel):
    name: str | None = None
    applies_to: PackageApplicationType | None = None
    credits_per_package: int | None = Field(default=None, ge=1)
    price: Decimal | None = Field(default=None, ge=Decimal("0"))
    active: bool | None = None


class PackageTypeRead(PackageTypeBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PackagePurchaseRequest(BaseModel):
    owner_id: uuid.UUID
    package_type_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class PackagePurchaseResponse(BaseModel):
    invoice_id: uuid.UUID


class PackageCreditApplicationRead(BaseModel):
    invoice_id: uuid.UUID
    applied_amount: Decimal
    units_consumed: Dict[str, int] = Field(default_factory=dict)


class GiftCertificateIssueRequest(BaseModel):
    purchaser_owner_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"))
    recipient_owner_id: uuid.UUID | None = None
    recipient_email: str | None = None
    expires_on: date | None = None


class GiftCertificateRead(BaseModel):
    id: uuid.UUID
    code: str
    original_value: Decimal
    remaining_value: Decimal
    purchaser_owner_id: uuid.UUID
    recipient_owner_id: uuid.UUID | None = None
    recipient_email: str | None = None
    expires_on: date | None = None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GiftCertificateRedeemRequest(BaseModel):
    code: str
    owner_id: uuid.UUID


class StoreCreditAddRequest(BaseModel):
    owner_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"))
    note: str | None = None


class StoreCreditBalanceResponse(BaseModel):
    owner_id: uuid.UUID
    balance: Decimal


class StoreCreditApplyRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))


class PackageBalanceRead(BaseModel):
    package_type_id: uuid.UUID
    name: str
    applies_to: str
    remaining: int


class StoreCreditSummary(BaseModel):
    balance: Decimal


class PortalStoreBalancesResponse(BaseModel):
    packages: list[PackageBalanceRead]
    store_credit: StoreCreditSummary


class PortalPackagePurchaseRequest(BaseModel):
    package_type_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class PortalPurchaseResponse(BaseModel):
    invoice_id: uuid.UUID
    client_secret: str | None = None
    transaction_id: uuid.UUID | None = None
    gift_certificate_id: uuid.UUID | None = None
    gift_certificate_code: str | None = None


class PortalGiftCertificatePurchaseRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    recipient_email: str | None = None


class PortalGiftCertificateRedeemRequest(BaseModel):
    code: str


class PortalStoreCreditApplyRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
