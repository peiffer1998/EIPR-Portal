"""Email and SMS notification helpers."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.models.immunization import ImmunizationStatus

logger = logging.getLogger(__name__)


def schedule_email(
    background_tasks: BackgroundTasks,
    *,
    recipients: Iterable[str],
    subject: str,
    body: str,
) -> None:
    """Queue an email to be delivered asynchronously."""
    recipients_list = [addr for addr in recipients if addr]
    if not recipients_list:
        logger.debug("No recipients provided for email; skipping")
        return
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_port:
        logger.debug("SMTP disabled; skipping email to %s", recipients_list)
        return
    background_tasks.add_task(_send_email, recipients_list, subject, body)


def schedule_sms(
    background_tasks: BackgroundTasks,
    *,
    phone_numbers: Iterable[str],
    message: str,
) -> None:
    """Queue an SMS notification (stub implementation)."""
    numbers = [number for number in phone_numbers if number]
    if not numbers:
        logger.debug("No phone numbers provided for SMS; skipping")
        return
    for number in numbers:
        background_tasks.add_task(_log_sms_stub, number, message)


def build_welcome_email(*, first_name: str) -> tuple[str, str]:
    subject = "Welcome to Eastern Iowa Pet Resort"
    body = (
        f"Hi {first_name},\n\n"
        "Thanks for creating an account with Eastern Iowa Pet Resort. "
        "You can now manage your pets, request services, and stay informed about their visits.\n\n"
        "We look forward to seeing you and your pet soon!\n"
        "-- Eastern Iowa Pet Resort Team"
    )
    return subject, body


def build_booking_confirmation_email(
    *, pet_name: str, start_at: str, end_at: str, location_name: str
) -> tuple[str, str]:
    subject = f"Booking confirmed for {pet_name}"
    body = (
        f"Hello,\n\nYour reservation for {pet_name} at {location_name} is confirmed.\n"
        f"Drop-off: {start_at}\nPick-up: {end_at}\n\n"
        "If you need to make changes, please contact our staff.\n\n"
        "Thank you for choosing Eastern Iowa Pet Resort!"
    )
    return subject, body


def build_check_in_notification(
    *, pet_name: str, location_name: str
) -> tuple[str, str]:
    subject = f"{pet_name} is checked in"
    body = (
        f"Hi there,\n\n{pet_name} has successfully checked in at {location_name}. "
        "We'll keep you updated throughout their stay!\n"
    )
    return subject, body


def build_invoice_email(*, invoice_number: str, total: str) -> tuple[str, str]:
    subject = f"Invoice {invoice_number} available"
    body = (
        f"Hello,\n\nYour invoice {invoice_number} totaling ${total} is ready. "
        "You can review and pay it through the client portal.\n\n"
        "Thank you for your business!"
    )
    return subject, body


def build_waitlist_offer_email(
    *,
    start_date: str,
    end_date: str,
    location_name: str,
    ttl_minutes: int,
    confirm_url: str,
) -> tuple[str, str]:
    subject = "Spot available at Eastern Iowa Pet Resort"
    body = (
        "Good news! A spot opened up for your reservation request.\n\n"
        f"Dates: {start_date} to {end_date}\n"
        f"Location: {location_name}\n\n"
        f"Confirm within {ttl_minutes} minutes using the link below:\n{confirm_url}\n\n"
        "If the link is not clickable, copy and paste it into your browser.\n\n"
        "We look forward to seeing you soon!\n"
    )
    return subject, body


def build_waitlist_offer_sms(
    *, start_date: str, end_date: str, ttl_minutes: int, confirm_url: str
) -> str:
    return (
        f"EIPR: Your spot is available for {start_date}-{end_date}. Confirm: {confirm_url}. "
        f"Expires in {ttl_minutes} min. Reply STOP to opt out."
    )


def build_payment_receipt_email(*, invoice_number: str, amount: str) -> tuple[str, str]:
    subject = f"Payment received for invoice {invoice_number}"
    body = (
        f"Hello,\n\nWe have received your payment of ${amount} for invoice {invoice_number}. "
        "Thank you!\n"
    )
    return subject, body


def build_password_reset_email(*, token: str) -> tuple[str, str]:
    subject = "Reset your Eastern Iowa Pet Resort password"
    body = (
        "Hello,\n\nWe received a request to reset your password. "
        f"Use the following token to complete the process: {token}\n"
        "If you did not request this change, you can ignore this message."
    )
    return subject, body


def build_immunization_alert_email(
    *,
    pet_name: str,
    immunization_name: str,
    status: ImmunizationStatus,
    expires_on: str | None,
) -> tuple[str, str]:
    if status is ImmunizationStatus.EXPIRED:
        subject = f"{pet_name}'s {immunization_name} has expired"
        timeline = "expired"
    else:
        subject = f"{pet_name}'s {immunization_name} expires soon"
        timeline = "will expire soon"
    body_lines = [
        "Hello,",
        "",
        f"This is a reminder that {pet_name}'s {immunization_name} {timeline}.",
    ]
    if expires_on:
        body_lines.append(f"Expiration date: {expires_on}")
    body_lines.extend(
        [
            "Please provide updated vaccination records before the next reservation.",
            "",
            "Thank you!",
        ]
    )
    return subject, "\n".join(body_lines)


def notify_immunization_alert(
    *, record, owner_user, background_tasks: BackgroundTasks
) -> None:
    pet = getattr(record, "pet", None)
    immunization_type = getattr(record, "immunization_type", None)
    if not owner_user or not immunization_type or not pet:
        return
    subject, body = build_immunization_alert_email(
        pet_name=getattr(pet, "name", "Your pet"),
        immunization_name=immunization_type.name,
        status=record.status,
        expires_on=record.expires_on.isoformat() if record.expires_on else None,
    )
    schedule_email(
        background_tasks,
        recipients=[owner_user.email],
        subject=subject,
        body=body,
    )
    if getattr(owner_user, "phone_number", None):
        status_phrase = (
            "has expired"
            if record.status is ImmunizationStatus.EXPIRED
            else "expires soon"
        )
        schedule_sms(
            background_tasks,
            phone_numbers=[owner_user.phone_number],
            message=f"Reminder: {getattr(pet, 'name', 'Your pet')}'s {immunization_type.name} {status_phrase}.",
        )


def build_staff_invitation_email(
    *, first_name: str, inviter_name: str, role: str, token: str
) -> tuple[str, str]:
    subject = "You're invited to join Eastern Iowa Pet Resort"
    body = (
        f"Hi {first_name},\n\n"
        f"{inviter_name} has invited you to join Eastern Iowa Pet Resort as a {role}. "
        "Use the invitation token below to complete your account setup within the next few days.\n\n"
        f"Invitation token: {token}\n"
        "Visit the staff portal and submit this token along with your preferred password to finish activation.\n\n"
        "If you weren't expecting this invite, you can safely ignore it."
    )
    return subject, body


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_port:
        logger.info("SMTP settings missing; skipping email delivery to %s", recipients)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = ", ".join(recipients)
    from_address = settings.smtp_username or "no-reply@eipr.local"
    message["From"] = from_address
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_username and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        logger.info("Email sent to %s", recipients)
    except Exception as exc:  # pragma: no cover - logging side-effect only
        logger.exception("Failed to send email to %s: %s", recipients, exc)


def _log_sms_stub(phone_number: str, message: str) -> None:
    logger.info("SMS to %s: %s", phone_number, message)


def notify_booking_confirmation(reservation, background_tasks: BackgroundTasks) -> None:
    owner_user = _extract_owner_user(reservation)
    if not owner_user:
        return
    pet = getattr(reservation, "pet", None)
    location_name = getattr(reservation.location, "name", "the resort")
    subject, body = build_booking_confirmation_email(
        pet_name=getattr(pet, "name", "Your pet"),
        start_at=reservation.start_at.isoformat(),
        end_at=reservation.end_at.isoformat(),
        location_name=location_name,
    )
    schedule_email(
        background_tasks,
        recipients=[owner_user.email],
        subject=subject,
        body=body,
    )
    if owner_user.phone_number:
        schedule_sms(
            background_tasks,
            phone_numbers=[owner_user.phone_number],
            message=f"Booking confirmed for {getattr(pet, 'name', 'your pet')} at {location_name}.",
        )


def notify_check_in(reservation, background_tasks: BackgroundTasks) -> None:
    owner_user = _extract_owner_user(reservation)
    if not owner_user:
        return
    pet = getattr(reservation, "pet", None)
    subject, body = build_check_in_notification(
        pet_name=getattr(pet, "name", "Your pet"),
        location_name=getattr(reservation.location, "name", "the resort"),
    )
    schedule_email(
        background_tasks,
        recipients=[owner_user.email],
        subject=subject,
        body=body,
    )


def notify_invoice_available(invoice, background_tasks: BackgroundTasks) -> None:
    owner_user = _extract_owner_user(getattr(invoice, "reservation", None))
    if not owner_user:
        return
    subject, body = build_invoice_email(
        invoice_number=str(invoice.id),
        total=f"{invoice.total_amount:.2f}",
    )
    schedule_email(
        background_tasks,
        recipients=[owner_user.email],
        subject=subject,
        body=body,
    )


def notify_payment_receipt(invoice, background_tasks: BackgroundTasks) -> None:
    owner_user = _extract_owner_user(getattr(invoice, "reservation", None))
    if not owner_user:
        return
    subject, body = build_payment_receipt_email(
        invoice_number=str(invoice.id),
        amount=f"{invoice.total_amount:.2f}",
    )
    schedule_email(
        background_tasks,
        recipients=[owner_user.email],
        subject=subject,
        body=body,
    )


def _extract_owner_user(reservation):
    if reservation is None:
        return None
    pet = getattr(reservation, "pet", None)
    owner = getattr(pet, "owner", None) if pet else None
    return getattr(owner, "user", None) if owner else None
