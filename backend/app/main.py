"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.api import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Return a simple welcome message."""
    return {"message": "Eastern Iowa Pet Resort API"}
