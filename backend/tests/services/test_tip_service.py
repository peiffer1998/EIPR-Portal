"""Tests for tip allocation logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest

from app.db.session import get_sessionmaker
from sqlalchemy import select

from app.models import (
    Account,
    Location,
    TimeClockPunch,
    TipPolicy,
    TipShare,
    User,
    UserRole,
    UserStatus,
)
from app.services import tip_service

pytestmark = pytest.mark.asyncio


async def _seed_staff(session) -> tuple[Account, Location, User, User]:
    account = Account(name="Tips Resort", slug=f"tips-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Iowa City", timezone="UTC")
    session.add(location)
    await session.flush()

    staff_one = User(
        account_id=account.id,
        email="staff1@example.com",
        hashed_password="x",
        first_name="Staff",
        last_name="One",
        role=UserRole.MANAGER,
        status=UserStatus.ACTIVE,
    )
    staff_two = User(
        account_id=account.id,
        email="staff2@example.com",
        hashed_password="x",
        first_name="Staff",
        last_name="Two",
        role=UserRole.STAFF,
        status=UserStatus.ACTIVE,
    )
    session.add_all([staff_one, staff_two])
    await session.commit()
    await session.refresh(staff_one)
    await session.refresh(staff_two)

    return account, location, staff_one, staff_two


async def test_pooled_by_hours_distribution(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, staff_one, staff_two = await _seed_staff(session)

        work_day = datetime(2025, 6, 1, 9, tzinfo=timezone.utc)

        session.add_all(
            [
                TimeClockPunch(
                    account_id=account.id,
                    location_id=location.id,
                    user_id=staff_one.id,
                    clock_in_at=work_day,
                    clock_out_at=work_day + timedelta(hours=2),
                    rounded_in_at=work_day,
                    rounded_out_at=work_day + timedelta(hours=2),
                    minutes_worked=120,
                ),
                TimeClockPunch(
                    account_id=account.id,
                    location_id=location.id,
                    user_id=staff_two.id,
                    clock_in_at=work_day,
                    clock_out_at=work_day + timedelta(hours=4),
                    rounded_in_at=work_day,
                    rounded_out_at=work_day + timedelta(hours=4),
                    minutes_worked=240,
                ),
            ]
        )
        await session.commit()

        tx = await tip_service.record_tip(
            session,
            account_id=account.id,
            location_id=location.id,
            d=work_day.date(),
            amount=Decimal("30.00"),
            policy=TipPolicy.POOLED_BY_HOURS,
        )

        shares_result = await session.execute(
            select(TipShare).where(TipShare.tip_transaction_id == tx.id)
        )
        shares = {share.user_id: share.amount for share in shares_result.scalars()}
        assert shares[staff_one.id] == Decimal("10.00")
        assert shares[staff_two.id] == Decimal("20.00")
        assert sum(shares.values()) == Decimal("30.00")


async def test_pooled_by_hours_remainder_assigned(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, staff_one, staff_two = await _seed_staff(session)

        work_day = datetime(2025, 6, 2, 9, tzinfo=timezone.utc)
        session.add_all(
            [
                TimeClockPunch(
                    account_id=account.id,
                    location_id=location.id,
                    user_id=staff_one.id,
                    clock_in_at=work_day,
                    clock_out_at=work_day + timedelta(hours=1),
                    rounded_in_at=work_day,
                    rounded_out_at=work_day + timedelta(hours=1),
                    minutes_worked=60,
                ),
                TimeClockPunch(
                    account_id=account.id,
                    location_id=location.id,
                    user_id=staff_two.id,
                    clock_in_at=work_day,
                    clock_out_at=work_day + timedelta(hours=1),
                    rounded_in_at=work_day,
                    rounded_out_at=work_day + timedelta(hours=1),
                    minutes_worked=60,
                ),
            ]
        )
        await session.commit()

        tx = await tip_service.record_tip(
            session,
            account_id=account.id,
            location_id=location.id,
            d=work_day.date(),
            amount=Decimal("10.00"),
            policy=TipPolicy.POOLED_BY_HOURS,
        )

        shares_result = await session.execute(
            select(TipShare)
            .where(TipShare.tip_transaction_id == tx.id)
            .order_by(TipShare.user_id)
        )
        amounts = [share.amount for share in shares_result.scalars()]
        # 10 / 2 = 5.00 exactly; ensure deterministic order retained
        assert amounts == [Decimal("5.00"), Decimal("5.00")]

        tx2 = await tip_service.record_tip(
            session,
            account_id=account.id,
            location_id=location.id,
            d=work_day.date(),
            amount=Decimal("10.01"),
            policy=TipPolicy.POOLED_BY_HOURS,
        )

        shares2_result = await session.execute(
            select(TipShare)
            .where(TipShare.tip_transaction_id == tx2.id)
            .order_by(TipShare.user_id)
        )
        amounts2 = [share.amount for share in shares2_result.scalars()]
        assert sum(amounts2) == Decimal("10.01")
        assert set(amounts2) == {Decimal("5.00"), Decimal("5.01")}
