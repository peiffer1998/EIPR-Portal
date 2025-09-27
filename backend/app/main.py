"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from secure import Secure
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis  # type: ignore[import-untyped]

from app.api import api_router
from app.core.config import get_settings
from app.security.logging_filters import SensitiveFilter
from app.services.bootstrap_service import ensure_default_admin

logger = logging.getLogger(__name__)

settings = get_settings()

_ALLOWED_ORIGINS = [origin for origin in settings.cors_allowlist if origin]
if not _ALLOWED_ORIGINS:
    _ALLOWED_ORIGINS = [origin for origin in settings.cors_allow_origins if origin]
if not _ALLOWED_ORIGINS:
    _ALLOWED_ORIGINS = ["http://localhost:5173"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_url = settings.redis_url or "redis://redis:6379/0"
    redis_pool = None
    try:
        redis_pool = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_pool)
        setattr(FastAPILimiter, "default_limits", [settings.rate_limit_default])
    except Exception:  # pragma: no cover - limiter startup is best effort
        logger.exception("Failed to initialize rate limiter")
    try:
        await ensure_default_admin()
    except Exception:  # pragma: no cover - best effort bootstrap
        logger.exception("Failed to ensure default admin account")
    try:
        yield
    finally:
        try:
            await FastAPILimiter.close()
        except Exception:  # pragma: no cover - limiter shutdown
            logger.exception("Failed to close rate limiter")
        finally:
            if redis_pool is not None:
                try:
                    await redis_pool.aclose()
                except Exception:
                    logger.exception("Failed to close redis pool")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

_secure_headers = Secure()


@app.middleware("http")
async def _apply_security_headers(request, call_next):
    response = await call_next(request)
    _secure_headers.set_headers(response)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        response.headers.setdefault("X-Request-ID", str(correlation_id))
    return response


for _logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", ""):
    _logger = logging.getLogger(_logger_name)
    if not any(isinstance(flt, SensitiveFilter) for flt in _logger.filters):
        _logger.addFilter(SensitiveFilter())

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Return a simple welcome message."""
    return {"message": "Eastern Iowa Pet Resort API"}
