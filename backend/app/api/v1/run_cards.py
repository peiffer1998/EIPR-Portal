"""Printable run card views."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.location import Location
from app.models.user import User, UserRole
from app.schemas.ops_p5 import RunCardContext
from app.services import feeding_board_service, medication_board_service

router = APIRouter(prefix="/run-cards")
logger = logging.getLogger("app.api.run_cards")

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent.parent / "templates")
)


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format",
        ) from exc


@router.get(
    "/print",
    response_class=HTMLResponse,
    summary="Render printable run cards",
)
async def print_run_cards(
    request: Request,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_value: str = Query(..., alias="date", description="Target date in YYYY-MM-DD"),
    location_id: uuid.UUID = Query(..., description="Location identifier"),
) -> HTMLResponse:
    _require_staff(current_user)
    target_date = _parse_date(date_value)

    location = await session.get(Location, location_id)
    if location is None or location.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location not found"
        )

    logger.info(
        "Run cards requested",
        extra={
            "account_id": str(current_user.account_id),
            "location_id": str(location_id),
            "date": target_date.isoformat(),
        },
    )

    feedings = await feeding_board_service.list_for_date(
        session,
        account_id=current_user.account_id,
        location_id=location_id,
        target_date=target_date,
    )
    medications = await medication_board_service.list_for_date(
        session,
        account_id=current_user.account_id,
        location_id=location_id,
        target_date=target_date,
    )

    context = RunCardContext(
        date=target_date,
        location_name=location.name,
        feedings=feedings,
        medications=medications,
    )

    return templates.TemplateResponse(
        request,
        "run_cards.html",
        {"context": context},
    )
