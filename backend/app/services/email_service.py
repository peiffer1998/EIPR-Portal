"""Email helpers for rich-content messages and transactional notifications."""

from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import EmailOutbox, EmailState, EmailTemplate, OwnerProfile
from app.schemas.report_card import ReportCardRead

logger = logging.getLogger(__name__)

__all__ = [
    "render_template",
    "send_email",
    "send_template",
    "send_report_card_email",
]

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
_STRING_ENV = Environment(autoescape=select_autoescape(["html", "xml"]))


def _render_report_card_html(card: ReportCardRead) -> str:
    template = _ENV.get_template("report_card_email.html")
    return template.render(
        pet_name=card.pet_name or "Your pet",
        occurred_on=card.occurred_on,
        summary=card.summary,
        rating=card.rating,
        media=card.media,
        friends=card.friends,
    )


def _deliver_email(to_email: str, subject: str, html_body: str) -> bool:
    """Attempt to deliver an email immediately.

    Returns True if a send was attempted (and succeeded), False if skipped due to
    missing SMTP configuration. Raises on transport errors.
    """

    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_port:
        logger.info("SMTP configuration missing; skipping email to %s", to_email)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = to_email
    message["From"] = (
        settings.smtp_from or settings.smtp_username or "no-reply@eipr.local"
    )
    message.set_content("This message contains HTML content.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
            if settings.smtp_username and settings.smtp_password:
                try:
                    server.starttls()
                except smtplib.SMTPException:
                    logger.debug("SMTP server does not support STARTTLS")
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - network dependent
        logger.exception("Failed to send email to %s: %s", to_email, exc)
        raise
    return True


async def _load_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile:
    stmt = (
        select(OwnerProfile)
        .options(selectinload(OwnerProfile.user))
        .where(OwnerProfile.id == owner_id)
    )
    result = await session.execute(stmt)
    owner = result.scalar_one_or_none()
    if owner is None or owner.user is None:
        raise ValueError("Owner not found")
    return owner


def _merge_context(
    owner: OwnerProfile, context: Mapping[str, Any] | None
) -> dict[str, Any]:
    base_context: dict[str, Any] = {
        "owner": {
            "first_name": owner.user.first_name,
            "last_name": owner.user.last_name,
            "email": owner.user.email,
        }
    }
    if context:
        for key, value in context.items():
            base_context[key] = value
    return base_context


def render_template(
    template: EmailTemplate, context: Mapping[str, Any] | None
) -> tuple[str, str]:
    subject_template = _STRING_ENV.from_string(template.subject_template)
    html_template = _STRING_ENV.from_string(template.html_template)
    ctx = dict(context or {})
    return subject_template.render(**ctx), html_template.render(**ctx)


async def send_email(
    session: AsyncSession,
    *,
    owner_id: UUID,
    subject: str,
    html: str,
    template: EmailTemplate | None = None,
) -> UUID:
    owner = await _load_owner(session, owner_id)
    if not owner.email_opt_in:
        raise ValueError("Owner has opted out of email communication")
    to_email = owner.user.email
    if not to_email:
        raise ValueError("Owner does not have an email address")

    outbox = EmailOutbox(
        account_id=owner.user.account_id,
        owner_id=owner_id,
        to_email=to_email,
        subject=subject,
        html=html,
        template_id=template.id if template else None,
        state=EmailState.QUEUED,
    )
    session.add(outbox)
    await session.flush()

    try:
        delivered = _deliver_email(to_email, subject, html)
    except Exception as exc:  # pragma: no cover
        outbox.state = EmailState.FAILED
        outbox.error = str(exc)
    else:
        outbox.state = EmailState.SENT
        outbox.sent_at = datetime.now(UTC)
        if not delivered:
            outbox.error = "delivery skipped (no SMTP configured)"
    await session.commit()
    return outbox.id


async def send_template(
    session: AsyncSession,
    *,
    owner_id: UUID,
    template_name: str,
    context: Mapping[str, Any] | None = None,
) -> UUID:
    owner = await _load_owner(session, owner_id)
    stmt = select(EmailTemplate).where(
        EmailTemplate.account_id == owner.user.account_id,
        EmailTemplate.name == template_name,
        EmailTemplate.active.is_(True),
    )
    template = (await session.execute(stmt)).scalar_one_or_none()
    if template is None:
        raise ValueError("Email template not found")

    merged = _merge_context(owner, context)
    subject, html = render_template(template, merged)
    return await send_email(
        session,
        owner_id=owner_id,
        subject=subject,
        html=html,
        template=template,
    )


def send_report_card_email(recipient: str, card: ReportCardRead) -> None:
    """Send a report card email to the pet parent."""

    if not recipient:
        logger.debug("Report card email skipped: no recipient")
        return

    subject = f"{card.pet_name or 'Your pet'}'s report card"
    html_body = _render_report_card_html(card)

    try:
        _deliver_email(recipient, subject, html_body)
    except Exception:  # pragma: no cover - network dependent
        logger.exception("Failed to send report card email to %s", recipient)
