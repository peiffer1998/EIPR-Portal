"""Versioned API router."""
from fastapi import APIRouter

from . import auth, capacity, health, owners, pets, reservations, users

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(owners.router, prefix="/owners", tags=["owners"])
router.include_router(pets.router, prefix="/pets", tags=["pets"])
router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
router.include_router(capacity.router, prefix="/capacity", tags=["capacity"])

__all__ = ["router"]
