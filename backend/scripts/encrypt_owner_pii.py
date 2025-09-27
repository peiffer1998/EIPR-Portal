"""One-time helper to encrypt existing PII records in place."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.staff_invitation import StaffInvitation
from app.models.store import GiftCertificate
from app.models.user import User

_PII_USER_FIELDS = ("email", "first_name", "last_name", "phone_number")
_PII_INVITATION_FIELDS = ("email", "first_name", "last_name", "phone_number")
_PII_GIFT_FIELDS = ("recipient_email",)


async def _reencrypt_model(session, model, fields: tuple[str, ...]) -> int:
    result = await session.execute(select(model))
    rows = result.scalars().all()
    updated = 0
    for row in rows:
        changed = False
        for field in fields:
            value = getattr(row, field, None)
            if isinstance(value, str) and value:
                setattr(row, field, value)
                changed = True
        if changed:
            session.add(row)
            updated += 1
    if updated:
        await session.commit()
    return updated


async def main() -> None:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user_updates = await _reencrypt_model(session, User, _PII_USER_FIELDS)
        invitation_updates = await _reencrypt_model(
            session, StaffInvitation, _PII_INVITATION_FIELDS
        )
        gift_updates = await _reencrypt_model(
            session, GiftCertificate, _PII_GIFT_FIELDS
        )
    print(
        "Re-encrypted users=%s staff_invitations=%s gift_certificates=%s"
        % (user_updates, invitation_updates, gift_updates)
    )


if __name__ == "__main__":
    asyncio.run(main())
