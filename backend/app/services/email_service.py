"""Email helpers for rich-content messages."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings
from app.schemas.report_card import ReportCardRead

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


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


def send_report_card_email(recipient: str, card: ReportCardRead) -> None:
    """Send a report card email to the pet parent."""

    if not recipient:
        logger.debug("Report card email skipped: no recipient")
        return

    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_port:
        logger.info(
            "SMTP configuration missing; skipping report card email to %s", recipient
        )
        return

    subject = f"{card.pet_name or 'Your pet'}'s report card"
    html_body = _render_report_card_html(card)

    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = recipient
    message["From"] = (
        settings.smtp_from or settings.smtp_username or "no-reply@eipr.local"
    )
    message.set_content(
        "Your pet's report card is ready. Please view the HTML version of this message for full details."
    )
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
        logger.exception("Failed to send report card email to %s: %s", recipient, exc)
