"""Versioned API router."""
from fastapi import APIRouter

from . import auth, health, users

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])

__all__ = ["router"]
