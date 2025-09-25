"""Versioned API router."""
from fastapi import APIRouter

from . import accounts, auth, capacity, feeding, health, invoices, locations, medication, owners, pets, reports, reservations, users

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

__all__ = ["router"]
