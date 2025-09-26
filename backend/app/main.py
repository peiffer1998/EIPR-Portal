"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.services.bootstrap_service import ensure_default_admin

settings = get_settings()

default_origin_regex = settings.cors_allow_origin_regex
if default_origin_regex is None and settings.app_env.lower() == "local":
    # Permit common localhost/private-network origins during local development.
    default_origin_regex = (
        r"http://("  # noqa: E501 - regex kept readable for future tweaks
        r"localhost|"
        r"127\.0\.0\.1|"
        r"10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|"
        r"192\.168\.[0-9]{1,3}\.[0-9]{1,3}|"
        r"172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}"
        r")(?:\:[0-9]{2,5})?$"
    )

allow_origins = settings.cors_allow_origins or ["*"]

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=default_origin_regex,
    allow_credentials=settings.cors_allow_credentials,
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
