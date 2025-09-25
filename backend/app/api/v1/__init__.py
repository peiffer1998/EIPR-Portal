"""Versioned API router."""
from fastapi import APIRouter

from . import (
    accounts,
    auth,
    capacity,
    documents,
    feeding,
    health,
    invoices,
    location_hours,
    locations,
    medication,
    owners,
    packages,
    pets,
    reports,
    reservations,
    service_catalog,
    users,
    waitlist,
)

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
router.include_router(locations.router, prefix="/locations", tags=["locations"])
router.include_router(owners.router, prefix="/owners", tags=["owners"])
router.include_router(pets.router, prefix="/pets", tags=["pets"])
router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
router.include_router(feeding.router, tags=["feeding"])
router.include_router(medication.router, tags=["medication"])
router.include_router(invoices.router, tags=["invoices"])
router.include_router(reports.router, tags=["reports"])
router.include_router(capacity.router, tags=["capacity"])
router.include_router(service_catalog.router, tags=["service-catalog"])
router.include_router(packages.router, tags=["packages"])
router.include_router(waitlist.router, tags=["waitlist"])
router.include_router(location_hours.router, tags=["location-hours"])
router.include_router(documents.router, tags=["documents"])

__all__ = ["router"]
