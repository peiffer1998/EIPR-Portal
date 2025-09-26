"""Communications management endpoints (email, SMS, campaigns, notifications)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models import (
    EmailState,
    CampaignSend,
    EmailOutbox,
    EmailTemplate,
    Notification,
    OwnerProfile,
    SMSConversation,
    SMSMessage,
    User,
    UserRole,
)
from app.schemas.comms import (
    CampaignPreviewRequest,
    CampaignPreviewResponse,
    CampaignSendNowRequest,
    CampaignSendRead,
    EmailSendRequest,
    EmailSendResponse,
    EmailTemplateCreate,
    EmailTemplateRead,
    EmailTemplateUpdate,
    SMSSendRequest,
    SMSConversationRead,
    SMSMessageRead,
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationRead,
)
from app.services import (
    campaigns_service,
    notifications_service,
    sms_service,
)
from app.services.email_service import (
    send_email as send_email_message,
    send_template as send_template_message,
)  # type: ignore[attr-defined]
from app.models.comms import NotificationType

router = APIRouter(prefix="/comms", tags=["comms"])


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


async def _fetch_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile:
    owner = await session.get(
        OwnerProfile,
        owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found"
        )
    return owner


async def _notify_account_staff(
    session: AsyncSession,
    *,
    account_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
) -> None:
    stmt: Select[User] = select(User).where(
        User.account_id == account_id,
        User.role != UserRole.PET_PARENT,
    )
    result = await session.execute(stmt)
    staff = result.scalars().all()
    for user in staff:
        await notifications_service.notify(
            session,
            account_id=account_id,
            user_id=user.id,
            type=notification_type,
            title=title,
            body=body,
        )


@router.post(
    "/emails/templates",
    response_model=EmailTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_email_template(
    payload: EmailTemplateCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> EmailTemplateRead:
    _require_staff(current_user)
    template = EmailTemplate(
        account_id=current_user.account_id,
        name=payload.name,
        subject_template=payload.subject_template,
        html_template=payload.html_template,
        active=payload.active,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return EmailTemplateRead.model_validate(template)


@router.get("/emails/templates", response_model=list[EmailTemplateRead])
async def list_email_templates(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[EmailTemplateRead]:
    _require_staff(current_user)
    stmt = (
        select(EmailTemplate)
        .where(EmailTemplate.account_id == current_user.account_id)
        .order_by(EmailTemplate.created_at.desc())
    )
    templates = (await session.execute(stmt)).scalars().all()
    return [EmailTemplateRead.model_validate(template) for template in templates]


@router.patch("/emails/templates/{template_id}", response_model=EmailTemplateRead)
async def update_email_template(
    template_id: UUID,
    payload: EmailTemplateUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> EmailTemplateRead:
    _require_staff(current_user)
    template = await session.get(EmailTemplate, template_id)
    if template is None or template.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    if payload.name is not None:
        template.name = payload.name
    if payload.subject_template is not None:
        template.subject_template = payload.subject_template
    if payload.html_template is not None:
        template.html_template = payload.html_template
    if payload.active is not None:
        template.active = payload.active
    await session.commit()
    await session.refresh(template)
    return EmailTemplateRead.model_validate(template)


@router.delete(
    "/emails/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_email_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _require_staff(current_user)
    template = await session.get(EmailTemplate, template_id)
    if template is None or template.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    await session.delete(template)
    await session.commit()


@router.post("/emails/send", response_model=EmailSendResponse)
async def send_email_endpoint(
    payload: EmailSendRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> EmailSendResponse:
    _require_staff(current_user)
    try:
        if payload.template_name:
            outbox_id = await send_template_message(
                session,
                owner_id=payload.owner_id,
                template_name=payload.template_name,
                context=payload.context,
            )
        else:
            if not payload.subject or not payload.html:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Subject and html are required when no template is specified",
                )
            outbox_id = await send_email_message(
                session,
                owner_id=payload.owner_id,
                subject=payload.subject,
                html=payload.html,
            )
    except ValueError as exc:  # raised by email service on invalid owner / template
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    outbox = await session.get(EmailOutbox, outbox_id)
    state = outbox.state if outbox is not None else None
    return EmailSendResponse(outbox_id=outbox_id, state=state or EmailState.QUEUED)


@router.get("/sms/conversations", response_model=list[SMSConversationRead])
async def list_sms_conversations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    owner_id: UUID | None = None,
) -> list[SMSConversationRead]:
    _require_staff(current_user)
    stmt = select(SMSConversation).where(
        SMSConversation.account_id == current_user.account_id
    )
    if owner_id is not None:
        stmt = stmt.where(SMSConversation.owner_id == owner_id)
    stmt = stmt.order_by(SMSConversation.last_message_at.desc())
    conversations = (await session.execute(stmt)).scalars().all()
    return [SMSConversationRead.model_validate(conv) for conv in conversations]


@router.get(
    "/sms/conversations/{conversation_id}/messages",
    response_model=list[SMSMessageRead],
)
async def list_sms_messages(
    conversation_id: UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[SMSMessageRead]:
    _require_staff(current_user)
    conversation = await session.get(
        SMSConversation,
        conversation_id,
        options=[selectinload(SMSConversation.messages)],
    )
    if conversation is None or conversation.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return [SMSMessageRead.model_validate(message) for message in conversation.messages]


@router.post(
    "/sms/send", response_model=SMSMessageRead, status_code=status.HTTP_201_CREATED
)
async def send_sms_message(
    payload: SMSSendRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> SMSMessageRead:
    _require_staff(current_user)
    message_id = await sms_service.send_sms(
        session,
        owner_id=payload.owner_id,
        body=payload.body,
    )
    message = await session.get(SMSMessage, message_id)
    assert message is not None  # service guarantees message exists
    return SMSMessageRead.model_validate(message)


@router.post("/sms/webhook", status_code=status.HTTP_202_ACCEPTED)
async def sms_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
) -> None:
    form = await request.form()
    from_number = form.get("From")
    body = form.get("Body")
    message_sid = form.get("MessageSid")
    if not from_number or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing fields"
        )
    try:
        phone_e164 = sms_service.normalize_phone(from_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    stmt = select(SMSConversation).where(SMSConversation.phone_e164 == phone_e164)
    conversation = (await session.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    await sms_service.record_inbound(
        session,
        account_id=conversation.account_id,
        owner_id=conversation.owner_id,
        phone_e164=phone_e164,
        body=body,
        provider_message_id=message_sid,
    )
    await _notify_account_staff(
        session,
        account_id=conversation.account_id,
        notification_type=NotificationType.MESSAGE,
        title="New owner message",
        body=f"Incoming SMS from {phone_e164}",
    )


@router.post(
    "/campaigns/preview",
    response_model=CampaignPreviewResponse,
)
async def preview_campaign(
    payload: CampaignPreviewRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> CampaignPreviewResponse:
    _require_staff(current_user)
    count = await campaigns_service.preview(
        session,
        account_id=current_user.account_id,
        segment=payload.segment,
    )
    return CampaignPreviewResponse(count=count)


@router.post(
    "/campaigns/send-now",
    response_model=list[CampaignSendRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_campaign_now(
    payload: CampaignSendNowRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[CampaignSendRead]:
    _require_staff(current_user)
    campaign_id = await campaigns_service.send_now(
        session,
        account_id=current_user.account_id,
        channel=payload.channel,
        template_name=payload.template_name,
        segment=payload.segment,
    )
    await session.commit()
    sends = (
        (
            await session.execute(
                select(CampaignSend).where(CampaignSend.campaign_id == campaign_id)
            )
        )
        .scalars()
        .all()
    )
    return [CampaignSendRead.model_validate(send) for send in sends]


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    unread_only: bool = False,
) -> NotificationListResponse:
    notifications = await notifications_service.list_for_user(
        session,
        account_id=current_user.account_id,
        user_id=current_user.id,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        notifications=[NotificationRead.model_validate(note) for note in notifications]
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationMarkReadResponse,
)
async def mark_notification_read(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> NotificationMarkReadResponse:
    await notifications_service.mark_read(
        session,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return NotificationMarkReadResponse(
        id=notification.id, read_at=notification.read_at
    )
