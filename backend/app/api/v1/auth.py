"""Authentication endpoints."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.account import Account
from app.schemas.auth import (
    InvitationAcceptResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetTokenResponse,
    RegistrationRequest,
    RegistrationResponse,
    StaffInvitationAcceptRequest,
    Token,
)
from app.schemas.owner import OwnerRead
from app.schemas.user import UserRead
from app.services import notification_service, owner_service, password_reset_service, staff_invitation_service, user_service
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


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED, summary="Register pet parent")
async def register_owner(
    payload: RegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
) -> RegistrationResponse:
    account_result = await session.execute(
        select(Account).where(Account.slug == payload.account_slug.lower())
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    existing = await user_service.get_user_by_email(session, email=payload.email.lower())
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    owner = await owner_service.create_owner(
        session,
        account_id=account.id,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        preferred_contact_method=payload.preferred_contact_method,
        notes=payload.notes,
        is_primary_contact=False,
    )
    token_value = await create_access_token_for_user(owner.user)
    subject, body = notification_service.build_welcome_email(first_name=owner.user.first_name)
    notification_service.schedule_email(
        background_tasks,
        recipients=[owner.user.email],
        subject=subject,
        body=body,
    )
    if owner.user.phone_number:
        notification_service.schedule_sms(
            background_tasks,
            phone_numbers=[owner.user.phone_number],
            message="Thanks for registering with Eastern Iowa Pet Resort!",
        )
    return RegistrationResponse(token=Token(access_token=token_value), owner=OwnerRead.model_validate(owner))


@router.post("/password-reset/request", response_model=PasswordResetTokenResponse, summary="Request password reset")
async def password_reset_request(
    payload: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
) -> PasswordResetTokenResponse:
    token_info = await password_reset_service.create_reset_token(session, email=payload.email)
    if token_info is None:
        return PasswordResetTokenResponse()
    raw_token, expires_at = token_info
    subject, body = notification_service.build_password_reset_email(token=raw_token)
    notification_service.schedule_email(
        background_tasks,
        recipients=[payload.email],
        subject=subject,
        body=body,
    )
    return PasswordResetTokenResponse(reset_token=raw_token, expires_at=expires_at)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT, summary="Confirm password reset")
async def password_reset_confirm(
    payload: PasswordResetConfirm,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await password_reset_service.consume_reset_token(
            session, token=payload.token, new_password=payload.new_password
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return None


@router.post("/invitations/accept", response_model=InvitationAcceptResponse, summary="Accept staff invitation")
async def accept_staff_invitation(
    payload: StaffInvitationAcceptRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
) -> InvitationAcceptResponse:
    try:
        _invitation, user = await staff_invitation_service.accept_invitation(
            session,
            token=payload.token,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_token = await create_access_token_for_user(user)
    subject, body = notification_service.build_welcome_email(first_name=user.first_name)
    notification_service.schedule_email(
        background_tasks,
        recipients=[user.email],
        subject=subject,
        body=body,
    )
    if user.phone_number:
        notification_service.schedule_sms(
            background_tasks,
            phone_numbers=[user.phone_number],
            message="Your staff account is ready at Eastern Iowa Pet Resort.",
        )
    return InvitationAcceptResponse(token=Token(access_token=access_token), user=UserRead.model_validate(user))
