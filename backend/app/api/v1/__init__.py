"""Versioned API router."""

from fastapi import APIRouter

from . import (
    accounts,
    agreements,
    auth,
    capacity,
    deposits,
    documents,
    feeding,
    feeding_board,
    health,
    icons,
    immunizations,
    invoices,
    location_hours,
    locations,
    medication,
    medication_board,
    owners,
    packages,
    pets,
    pricing,
    reports,
    reservations,
    run_cards,
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
router.include_router(
    reservations.router, prefix="/reservations", tags=["reservations"]
)
router.include_router(feeding.router, tags=["feeding"])
router.include_router(medication.router, tags=["medication"])
router.include_router(invoices.router, tags=["invoices"])
router.include_router(pricing.router, tags=["pricing"])
router.include_router(deposits.router, tags=["deposits"])
router.include_router(
    immunizations.router, prefix="/immunizations", tags=["immunizations"]
)
router.include_router(agreements.router, prefix="/agreements", tags=["agreements"])
router.include_router(icons.router, prefix="/icons", tags=["icons"])
router.include_router(reports.router, tags=["reports"])
router.include_router(capacity.router, tags=["capacity"])
router.include_router(service_catalog.router, tags=["service-catalog"])
router.include_router(packages.router, tags=["packages"])
router.include_router(waitlist.router, tags=["waitlist"])
router.include_router(location_hours.router, tags=["location-hours"])
router.include_router(documents.router, tags=["documents"])
# BEGIN OPS_P5 ROUTES
router.include_router(feeding_board.router, prefix="/feeding", tags=["feeding"])
router.include_router(
    medication_board.router, prefix="/medication", tags=["medication"]
)
router.include_router(run_cards.router, tags=["run-cards"])
# END OPS_P5 ROUTES

__all__ = ["router"]
