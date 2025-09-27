"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("", summary="Service health status")
async def healthcheck() -> dict[str, str]:
    """Return application health metadata."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.app_env,
    }
