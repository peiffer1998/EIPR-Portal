"""API router modules."""

from fastapi import APIRouter

from app.core.config import get_settings

from .v1 import router as api_v1_router

settings = get_settings()

api_router = APIRouter()
api_router.include_router(api_v1_router, prefix=settings.api_v1_prefix)

__all__ = ["api_router"]
