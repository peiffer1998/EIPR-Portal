"""Tests for report card service layer."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TypedDict

import pytest
import pytest_asyncio

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import (
    Account,
    Document,
    Location,
    OwnerProfile,
    Pet,
    PetType,
    ReportCardStatus,
    Reservation,
    ReservationStatus,
    ReservationType,
    User,
    UserRole,
    UserStatus,
)
from app.services.report_card_service import (
    attach_media,
    create_card,
    get_card,
    list_cards,
    mark_sent,
    set_friends,
)


class ReportCardFixture(TypedDict):
    account_id: uuid.UUID
    owner_id: uuid.UUID
    pet_id: uuid.UUID
    friend_pet_id: uuid.UUID
    staff_user_id: uuid.UUID
    reservation_id: uuid.UUID
    document_ids: list[uuid.UUID]


@pytest_asyncio.fixture()
async def report_card_setup(reset_database: None) -> ReportCardFixture:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        account = Account(name="EIPR", slug="eipr")
        session.add(account)
        await session.flush()

        staff_user = User(
            account_id=account.id,
            email="staff@example.com",
            hashed_password=get_password_hash("StaffP@ss1"),
            first_name="Sam",
            last_name="Staff",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
        )
        session.add(staff_user)

        owner_user = User(
            account_id=account.id,
            email="owner@example.com",
            hashed_password=get_password_hash("OwnerP@ss1"),
            first_name="Olivia",
            last_name="Owner",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(owner_user)
        await session.flush()

        owner = OwnerProfile(user_id=owner_user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(owner_id=owner.id, name="Rex", pet_type=PetType.DOG)
        session.add(pet)
        await session.flush()

        friend_pet = Pet(owner_id=owner.id, name="Milo", pet_type=PetType.DOG)
        session.add(friend_pet)
        await session.flush()

        location = Location(account_id=account.id, name="Main", timezone="UTC")
        session.add(location)
        await session.flush()

        reservation = Reservation(
            account_id=account.id,
            location_id=location.id,
            pet_id=pet.id,
            reservation_type=ReservationType.BOARDING,
            status=ReservationStatus.CONFIRMED,
            start_at=datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            end_at=datetime(2025, 1, 2, 9, 0, tzinfo=UTC),
            base_rate=Decimal("0"),
        )
        session.add(reservation)
        await session.flush()

        doc_one = Document(
            account_id=account.id,
            owner_id=owner.id,
            pet_id=pet.id,
            uploaded_by_user_id=staff_user.id,
            file_name="playtime.jpg",
            content_type="image/jpeg",
            object_key="documents/playtime.jpg",
            url="https://cdn.example.com/playtime.jpg",
        )
        session.add(doc_one)

        doc_two = Document(
            account_id=account.id,
            owner_id=owner.id,
            pet_id=pet.id,
            uploaded_by_user_id=staff_user.id,
            file_name="naptime.jpg",
            content_type="image/jpeg",
            object_key="documents/naptime.jpg",
            url="https://cdn.example.com/naptime.jpg",
        )
        session.add(doc_two)

        await session.commit()

        return {
            "account_id": account.id,
            "owner_id": owner.id,
            "pet_id": pet.id,
            "friend_pet_id": friend_pet.id,
            "staff_user_id": staff_user.id,
            "reservation_id": reservation.id,
            "document_ids": [doc_one.id, doc_two.id],
        }


@pytest.mark.asyncio
async def test_create_and_get_report_card(
    report_card_setup: ReportCardFixture,
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        card = await create_card(
            session,
            account_id=report_card_setup["account_id"],
            owner_id=report_card_setup["owner_id"],
            pet_id=report_card_setup["pet_id"],
            created_by_user_id=report_card_setup["staff_user_id"],
            occurred_on=date(2025, 1, 5),
            title="Daily Update",
            summary="Rex enjoyed a walk and a nap.",
            rating=5,
            reservation_id=report_card_setup["reservation_id"],
        )
        assert card.status == ReportCardStatus.DRAFT

        read = await get_card(
            session,
            account_id=report_card_setup["account_id"],
            card_id=card.id,
        )
        assert read.title == "Daily Update"
        assert read.pet_name == "Rex"
        assert read.owner_name is not None
        assert read.media == []
        assert read.friends == []


@pytest.mark.asyncio
async def test_attach_media_and_friends(
    report_card_setup: ReportCardFixture,
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        card = await create_card(
            session,
            account_id=report_card_setup["account_id"],
            owner_id=report_card_setup["owner_id"],
            pet_id=report_card_setup["pet_id"],
            created_by_user_id=report_card_setup["staff_user_id"],
            occurred_on=date(2025, 1, 6),
        )

        await attach_media(
            session,
            account_id=report_card_setup["account_id"],
            card_id=card.id,
            document_ids=list(report_card_setup["document_ids"]),
        )

        await set_friends(
            session,
            account_id=report_card_setup["account_id"],
            card_id=card.id,
            friend_pet_ids=[report_card_setup["friend_pet_id"]],
        )

        read = await get_card(
            session,
            account_id=report_card_setup["account_id"],
            card_id=card.id,
        )

        assert len(read.media) == 2
        assert read.media[0].display_url == "https://cdn.example.com/playtime.jpg"
        assert len(read.friends) == 1
        assert read.friends[0].id == report_card_setup["friend_pet_id"]


@pytest.mark.asyncio
async def test_list_cards_and_mark_sent(
    report_card_setup: ReportCardFixture,
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        first = await create_card(
            session,
            account_id=report_card_setup["account_id"],
            owner_id=report_card_setup["owner_id"],
            pet_id=report_card_setup["pet_id"],
            created_by_user_id=report_card_setup["staff_user_id"],
            occurred_on=date(2025, 1, 4),
        )
        second = await create_card(
            session,
            account_id=report_card_setup["account_id"],
            owner_id=report_card_setup["owner_id"],
            pet_id=report_card_setup["pet_id"],
            created_by_user_id=report_card_setup["staff_user_id"],
            occurred_on=date(2025, 1, 6),
        )

        await mark_sent(
            session,
            account_id=report_card_setup["account_id"],
            card_id=first.id,
        )

        cards = await list_cards(
            session,
            account_id=report_card_setup["account_id"],
            pet_id=report_card_setup["pet_id"],
            date_from=date(2025, 1, 5),
        )

        assert len(cards) == 1
        assert cards[0].id == second.id
        assert cards[0].status == ReportCardStatus.DRAFT

        all_cards = await list_cards(
            session,
            account_id=report_card_setup["account_id"],
        )
        statuses = {card.id: card.status for card in all_cards}
        assert statuses[first.id] == ReportCardStatus.SENT
        assert statuses[second.id] == ReportCardStatus.DRAFT
