"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.api.deps import get_db_session
from app.models.account import Account
from app.models.user import User
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
from app.core.config import get_settings
from app.services import (
    audit_service,
    notification_service,
    owner_service,
    password_reset_service,
    staff_invitation_service,
    user_service,
)
from app.services.auth_service import authenticate_user, create_access_token_for_user

router = APIRouter()

_settings = get_settings()

_DEF_LIMITS = _settings.rate_limit_default
_LOGIN_LIMITS = _settings.rate_limit_login


def _parse_rate(value: str, *, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        count_str, window_str = value.split("/", 1)
        count = int(count_str.strip())
    except Exception:
        return fallback
    window = window_str.strip().lower()
    seconds_map = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
        "day": 86400,
        "days": 86400,
    }
    seconds = seconds_map.get(window, fallback[1])
    return count, seconds


_LOGIN_LIMIT = _parse_rate(_LOGIN_LIMITS, fallback=(10, 60))
_DEFAULT_LIMIT = _parse_rate(_DEF_LIMITS, fallback=(100, 60))


def _rate_dependency(limit: tuple[int, int]):
    async def _dependency(request: Request, response: Response) -> None:
        if FastAPILimiter.redis is None:
            return None
        limiter = RateLimiter(times=limit[0], seconds=limit[1])
        await limiter(request, response)

    return Depends(_dependency)


_LOGIN_RATE_DEP = _rate_dependency(_LOGIN_LIMIT)
_DEFAULT_RATE_DEP = _rate_dependency(_DEFAULT_LIMIT)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _event_payload_for_user(user: User) -> dict[str, str]:
    return {"user_id": str(user.id), "email": user.email}


@router.post(
    "/token",
    response_model=Token,
    summary="Obtain access token",
    dependencies=[_LOGIN_RATE_DEP],
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> Token:
    """Validate credentials and issue a bearer token."""
    user = await authenticate_user(
        session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_access_token_for_user(user)
    await audit_service.record_event(
        session,
        account_id=user.account_id,
        user_id=user.id,
        event_type="auth.login",
        description="Successful login",
        payload=_event_payload_for_user(user),
        ip_address=_client_ip(request),
    )
    return Token(access_token=access_token)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register pet parent",
    dependencies=[_DEFAULT_RATE_DEP],
)
async def register_owner(
    payload: RegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
    request: Request,
) -> RegistrationResponse:
    account_result = await session.execute(
        select(Account).where(Account.slug == payload.account_slug.lower())
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    existing = await user_service.get_user_by_email(
        session, email=payload.email.lower()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

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
    subject, body = notification_service.build_welcome_email(
        first_name=owner.user.first_name
    )
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
    await audit_service.record_event(
        session,
        account_id=owner.user.account_id,
        user_id=owner.user.id,
        event_type="auth.register.pet_parent",
        description="Pet parent self-registration",
        payload={"owner_id": str(owner.id), **_event_payload_for_user(owner.user)},
        ip_address=_client_ip(request),
    )
    return RegistrationResponse(
        token=Token(access_token=token_value), owner=OwnerRead.model_validate(owner)
    )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetTokenResponse,
    summary="Request password reset",
    dependencies=[_DEFAULT_RATE_DEP],
)
async def password_reset_request(
    payload: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
    request: Request,
) -> PasswordResetTokenResponse:
    token_info = await password_reset_service.create_reset_token(
        session, email=payload.email
    )
    client_ip = _client_ip(request)
    if token_info is None:
        # log the attempt without tying it to an account
        await audit_service.record_event(
            session,
            account_id=None,
            user_id=None,
            event_type="auth.password_reset.requested",
            description="Password reset requested for unknown email",
            payload={"email": payload.email.lower()},
            ip_address=client_ip,
        )
        return PasswordResetTokenResponse()

    raw_token, expires_at, user = token_info
    subject, body = notification_service.build_password_reset_email(token=raw_token)
    notification_service.schedule_email(
        background_tasks,
        recipients=[payload.email],
        subject=subject,
        body=body,
    )
    await audit_service.record_event(
        session,
        account_id=user.account_id,
        user_id=user.id,
        event_type="auth.password_reset.requested",
        description="Password reset email sent",
        payload=_event_payload_for_user(user),
        ip_address=client_ip,
    )
    return PasswordResetTokenResponse(reset_token=raw_token, expires_at=expires_at)


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm password reset",
)
async def password_reset_confirm(
    payload: PasswordResetConfirm,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> None:
    try:
        user = await password_reset_service.consume_reset_token(
            session, token=payload.token, new_password=payload.new_password
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await audit_service.record_event(
        session,
        account_id=user.account_id,
        user_id=user.id,
        event_type="auth.password_reset.completed",
        description="Password reset completed",
        payload=_event_payload_for_user(user),
        ip_address=_client_ip(request),
    )
    return None


@router.post(
    "/invitations/accept",
    response_model=InvitationAcceptResponse,
    summary="Accept staff invitation",
)
async def accept_staff_invitation(
    payload: StaffInvitationAcceptRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
    request: Request,
) -> InvitationAcceptResponse:
    try:
        invitation, user = await staff_invitation_service.accept_invitation(
            session,
            token=payload.token,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

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
    await audit_service.record_event(
        session,
        account_id=user.account_id,
        user_id=user.id,
        event_type="auth.invitation.accepted",
        description="Staff invitation accepted",
        payload={"invitation_id": str(invitation.id), **_event_payload_for_user(user)},
        ip_address=_client_ip(request),
    )
    return InvitationAcceptResponse(
        token=Token(access_token=access_token), user=UserRead.model_validate(user)
    )
