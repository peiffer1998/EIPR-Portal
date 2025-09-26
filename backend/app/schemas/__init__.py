"""Schema exports."""

from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.agreement import (
    AgreementSignatureCreate,
    AgreementSignatureRead,
    AgreementTemplateCreate,
    AgreementTemplateRead,
    AgreementTemplateUpdate,
)
from app.schemas.auth import (
    InvitationAcceptResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetTokenResponse,
    RegistrationRequest,
    RegistrationResponse,
    StaffInvitationAcceptRequest,
    Token,
)
from app.schemas.capacity import (
    LocationCapacityRuleCreate,
    LocationCapacityRuleRead,
    LocationCapacityRuleUpdate,
)
from app.schemas.deposit import DepositActionRequest, DepositRead
from app.schemas.document import DocumentCreate, DocumentRead
from app.schemas.feeding import (
    FeedingScheduleCreate,
    FeedingScheduleRead,
    FeedingScheduleUpdate,
)
from app.schemas.icon import (
    IconCreate,
    IconRead,
    IconUpdate,
    OwnerIconAssignmentCreate,
    OwnerIconAssignmentRead,
    PetIconAssignmentCreate,
    PetIconAssignmentRead,
)
from app.schemas.immunization import (
    ImmunizationRecordCreate,
    ImmunizationRecordRead,
    ImmunizationRecordUpdate,
    ImmunizationRecordStatus,
    ImmunizationTypeCreate,
    ImmunizationTypeRead,
    ImmunizationTypeUpdate,
)
from app.schemas.invoice import (
    InvoiceApplyPromotionRequest,
    InvoiceFromReservationRequest,
    InvoiceItemCreate,
    InvoiceItemRead,
    InvoicePaymentRequest,
    InvoiceRead,
    InvoiceTotalsRead,
)
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate
from app.schemas.location_hours import (
    LocationClosureCreate,
    LocationClosureRead,
    LocationHourCreate,
    LocationHourRead,
    LocationHourUpdate,
)
from app.schemas.medication import (
    MedicationScheduleCreate,
    MedicationScheduleRead,
    MedicationScheduleUpdate,
)
from app.schemas.owner import (
    OwnerCreate,
    OwnerRead,
    OwnerReservationRequest,
    OwnerUpdate,
)
from app.schemas.package import (
    ServicePackageCreate,
    ServicePackageRead,
    ServicePackageUpdate,
)
from app.schemas.pet import PetCreate, PetRead, PetUpdate
from app.schemas.pricing import (
    PricingLineRead,
    PricingQuoteRead,
    PricingQuoteRequest,
)
from app.schemas.reporting import OccupancyEntry, RevenueEntry, RevenueReport
from app.schemas.reservation import (
    ReservationCreate,
    ReservationRead,
    ReservationUpdate,
)
from app.schemas.scheduling import (
    AvailabilityRequest,
    AvailabilityResponse,
    DailyAvailability,
)
from app.schemas.service_catalog import (
    ServiceCatalogItemCreate,
    ServiceCatalogItemRead,
    ServiceCatalogItemUpdate,
)
from app.schemas.user import (
    StaffInvitationCreate,
    StaffInvitationRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.schemas.waitlist import (
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistStatusUpdate,
)

__all__ = [
    "AccountCreate",
    "AccountRead",
    "AccountUpdate",
    "RegistrationRequest",
    "RegistrationResponse",
    "PasswordResetRequest",
    "PasswordResetTokenResponse",
    "PasswordResetConfirm",
    "StaffInvitationAcceptRequest",
    "InvitationAcceptResponse",
    "Token",
    "LocationCapacityRuleCreate",
    "LocationCapacityRuleRead",
    "LocationCapacityRuleUpdate",
    "FeedingScheduleCreate",
    "FeedingScheduleRead",
    "FeedingScheduleUpdate",
    "InvoiceFromReservationRequest",
    "InvoiceApplyPromotionRequest",
    "InvoiceItemCreate",
    "InvoiceItemRead",
    "InvoicePaymentRequest",
    "InvoiceRead",
    "InvoiceTotalsRead",
    "LocationCreate",
    "OccupancyEntry",
    "RevenueEntry",
    "RevenueReport",
    "LocationRead",
    "LocationUpdate",
    "MedicationScheduleCreate",
    "MedicationScheduleRead",
    "MedicationScheduleUpdate",
    "StaffInvitationCreate",
    "StaffInvitationRead",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "OwnerCreate",
    "OwnerRead",
    "OwnerReservationRequest",
    "OwnerUpdate",
    "ServiceCatalogItemCreate",
    "ServiceCatalogItemRead",
    "ServiceCatalogItemUpdate",
    "ServicePackageCreate",
    "ServicePackageRead",
    "ServicePackageUpdate",
    "WaitlistEntryCreate",
    "WaitlistEntryRead",
    "WaitlistStatusUpdate",
    "LocationHourCreate",
    "LocationHourRead",
    "LocationHourUpdate",
    "LocationClosureCreate",
    "LocationClosureRead",
    "DocumentCreate",
    "DocumentRead",
    "ImmunizationTypeCreate",
    "ImmunizationTypeRead",
    "ImmunizationTypeUpdate",
    "ImmunizationRecordCreate",
    "ImmunizationRecordRead",
    "ImmunizationRecordUpdate",
    "ImmunizationRecordStatus",
    "AgreementTemplateCreate",
    "AgreementTemplateRead",
    "AgreementTemplateUpdate",
    "AgreementSignatureCreate",
    "AgreementSignatureRead",
    "IconCreate",
    "IconRead",
    "IconUpdate",
    "OwnerIconAssignmentCreate",
    "OwnerIconAssignmentRead",
    "PetIconAssignmentCreate",
    "PetIconAssignmentRead",
    "DepositActionRequest",
    "DepositRead",
    "PricingLineRead",
    "PricingQuoteRead",
    "PricingQuoteRequest",
    "PetCreate",
    "PetRead",
    "PetUpdate",
    "ReservationCreate",
    "ReservationRead",
    "ReservationUpdate",
    "AvailabilityRequest",
    "AvailabilityResponse",
    "DailyAvailability",
]
