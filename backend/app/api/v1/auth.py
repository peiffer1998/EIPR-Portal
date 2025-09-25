"""Authentication endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.auth import Token
from app.services.auth_service import authenticate_user, create_access_token_for_user

router = APIRouter()


@router.post("/token", response_model=Token, summary="Obtain access token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    """Validate credentials and issue a bearer token."""
    user = await authenticate_user(session, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_access_token_for_user(user)
    return Token(access_token=access_token)
