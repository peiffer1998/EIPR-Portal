"""Account management services."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate


async def list_accounts(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Account]:
    """Return paginated accounts ordered by creation date."""
    stmt: Select[tuple[Account]] = (
        select(Account)
        .offset(skip)
        .limit(min(limit, 100))
        .order_by(Account.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_account(session: AsyncSession, account_id: uuid.UUID) -> Account | None:
    """Fetch a single account by identifier."""
    return await session.get(Account, account_id)


async def create_account(session: AsyncSession, payload: AccountCreate) -> Account:
    """Create a new account."""
    account = Account(name=payload.name, slug=payload.slug)
    session.add(account)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(account)
    return account


async def update_account(
    session: AsyncSession,
    account: Account,
    payload: AccountUpdate,
) -> Account:
    """Update fields on an account."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await session.commit()
    await session.refresh(account)
    return account


async def delete_account(session: AsyncSession, account: Account) -> None:
    """Delete an account."""
    await session.delete(account)
    await session.commit()
