"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.services.bootstrap_service import ensure_default_admin

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.on_event("startup")
async def bootstrap_defaults() -> None:
    try:
        await ensure_default_admin()
    except Exception:  # pragma: no cover - best effort bootstrap
        logger.exception("Failed to ensure default admin account")


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Return a simple welcome message."""
    return {"message": "Eastern Iowa Pet Resort API"}


logger = logging.getLogger(__name__)
