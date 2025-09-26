"""Report card service layer."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Final

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations import S3Client
from app.models import (
    Document,
    OwnerProfile,
    Pet,
    ReportCard,
    ReportCardMedia,
    ReportCardStatus,
    Reservation,
    User,
)
from app.schemas.document import DocumentRead
from app.schemas.report_card import (
    ReportCardMediaRead,
    ReportCardRead,
    ReportCardFriendRead,
)

_FRIEND_LOAD_OPTIONS: Final = [
    selectinload(ReportCard.friends),
    selectinload(ReportCard.media).selectinload(ReportCardMedia.document),
    selectinload(ReportCard.pet),
    selectinload(ReportCard.owner).selectinload(OwnerProfile.user),
    selectinload(ReportCard.created_by),
]


def _now() -> datetime:
    return datetime.now(UTC)


async def _get_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> OwnerProfile:
    owner = await session.get(
        OwnerProfile,
        owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Owner not found for account")
    return owner


async def _get_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
) -> Pet:
    pet = await session.get(
        Pet,
        pet_id,
        options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
    )
    if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Pet not found for account")
    return pet


async def _get_user(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User:
    user = await session.get(User, user_id)
    if user is None or user.account_id != account_id:
        raise ValueError("User not found for account")
    return user


async def _get_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None or reservation.account_id != account_id:
        raise ValueError("Reservation not found for account")
    return reservation


async def _get_card(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    card_id: uuid.UUID,
    eager: bool = True,
) -> ReportCard:
    if eager:
        stmt: Select[tuple[ReportCard]] = (
            select(ReportCard)
            .where(ReportCard.id == card_id, ReportCard.account_id == account_id)
            .options(*_FRIEND_LOAD_OPTIONS)
        )
        result = await session.execute(stmt)
        card = result.scalar_one_or_none()
    else:
        card = await session.get(ReportCard, card_id)
    if card is None or card.account_id != account_id:
        raise ValueError("Report card not found")
    return card


def _document_to_read(
    document: Document,
    *,
    s3_client: S3Client | None,
) -> DocumentRead:
    data = DocumentRead.model_validate(document)
    if document.object_key and not data.url and s3_client:
        data.url = s3_client.build_object_url(document.object_key)
    if document.object_key_web and s3_client:
        data.url_web = s3_client.build_object_url(document.object_key_web)
    if document.content_type_web and not data.content_type_web:
        data.content_type_web = document.content_type_web
    return data


def _media_to_read(
    media: ReportCardMedia,
    *,
    s3_client: S3Client | None,
) -> ReportCardMediaRead:
    document = media.document
    document_read = _document_to_read(document, s3_client=s3_client)
    display_url = document_read.url_web or document_read.url
    return ReportCardMediaRead(
        id=media.id,
        report_card_id=media.report_card_id,
        position=media.position,
        document=document_read,
        display_url=display_url,
    )


def _friends_to_read(card: ReportCard) -> list[ReportCardFriendRead]:
    friends: list[ReportCardFriendRead] = []
    for friend in card.friends:
        friends.append(
            ReportCardFriendRead(
                id=friend.id,
                owner_id=friend.owner_id,
                name=friend.name,
                pet_type=friend.pet_type,
            )
        )
    return friends


def _card_to_read(
    card: ReportCard,
    *,
    s3_client: S3Client | None,
) -> ReportCardRead:
    return ReportCardRead(
        id=card.id,
        account_id=card.account_id,
        owner_id=card.owner_id,
        pet_id=card.pet_id,
        reservation_id=card.reservation_id,
        occurred_on=card.occurred_on,
        title=card.title,
        summary=card.summary,
        rating=card.rating,
        status=card.status,
        created_by_user_id=card.created_by_user_id,
        sent_at=card.sent_at,
        created_at=card.created_at,
        updated_at=card.updated_at,
        media=[_media_to_read(media, s3_client=s3_client) for media in card.media],
        friends=_friends_to_read(card),
        pet_name=card.pet.name if card.pet else None,
        owner_name=(
            f"{card.owner.user.first_name} {card.owner.user.last_name}"
            if card.owner and card.owner.user
            else None
        ),
    )


async def create_card(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    pet_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    occurred_on: date,
    title: str | None = None,
    summary: str | None = None,
    rating: int | None = None,
    reservation_id: uuid.UUID | None = None,
) -> ReportCard:
    owner = await _get_owner(session, account_id=account_id, owner_id=owner_id)
    pet = await _get_pet(session, account_id=account_id, pet_id=pet_id)
    await _get_user(session, account_id=account_id, user_id=created_by_user_id)

    if pet.owner_id != owner.id:
        raise ValueError("Pet does not belong to owner")

    if reservation_id is not None:
        reservation = await _get_reservation(
            session, account_id=account_id, reservation_id=reservation_id
        )
        if reservation.pet_id != pet_id:
            raise ValueError("Reservation does not belong to pet")

    card = ReportCard(
        account_id=account_id,
        owner_id=owner_id,
        pet_id=pet_id,
        reservation_id=reservation_id,
        occurred_on=occurred_on,
        title=title,
        summary=summary,
        rating=rating,
        created_by_user_id=created_by_user_id,
        status=ReportCardStatus.DRAFT,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card


async def attach_media(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    card_id: uuid.UUID,
    document_ids: Sequence[uuid.UUID],
) -> ReportCard:
    card = await _get_card(session, account_id=account_id, card_id=card_id, eager=True)

    stmt = select(Document).where(
        Document.account_id == account_id, Document.id.in_(document_ids)
    )
    result = await session.execute(stmt)
    documents = {doc.id: doc for doc in result.scalars().all()}
    if len(documents) != len(set(document_ids)):
        raise ValueError("One or more documents not found for account")

    card.media.clear()
    for position, document_id in enumerate(document_ids):
        card.media.append(
            ReportCardMedia(
                report_card_id=card.id,
                document_id=document_id,
                position=position,
            )
        )

    await session.commit()
    await session.refresh(card)
    return card


async def set_friends(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    card_id: uuid.UUID,
    friend_pet_ids: Sequence[uuid.UUID],
) -> ReportCard:
    card = await _get_card(session, account_id=account_id, card_id=card_id, eager=True)

    if not friend_pet_ids:
        card.friends.clear()
        await session.commit()
        await session.refresh(card)
        return card

    stmt = (
        select(Pet)
        .where(Pet.id.in_(friend_pet_ids))
        .options(selectinload(Pet.owner).selectinload(OwnerProfile.user))
    )
    result = await session.execute(stmt)
    friends = result.scalars().all()

    if len(friends) != len(set(friend_pet_ids)):
        raise ValueError("Friend pet not found")

    for friend in friends:
        if friend.owner.user.account_id != account_id:  # type: ignore[union-attr]
            raise ValueError("Friend pet belongs to different account")

    order = {pet_id: index for index, pet_id in enumerate(friend_pet_ids)}
    friends_sorted = sorted(friends, key=lambda pet: order.get(pet.id, 0))
    card.friends = friends_sorted
    await session.commit()
    await session.refresh(card)
    return card


async def mark_sent(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    card_id: uuid.UUID,
    sent_at: datetime | None = None,
) -> ReportCard:
    card = await _get_card(session, account_id=account_id, card_id=card_id, eager=False)
    card.status = ReportCardStatus.SENT
    card.sent_at = sent_at or _now()
    await session.commit()
    await session.refresh(card)
    return card


async def get_card(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    card_id: uuid.UUID,
    s3_client: S3Client | None = None,
) -> ReportCardRead:
    card = await _get_card(session, account_id=account_id, card_id=card_id, eager=True)
    return _card_to_read(card, s3_client=s3_client)


async def list_cards(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
    pet_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    s3_client: S3Client | None = None,
) -> list[ReportCardRead]:
    stmt: Select[tuple[ReportCard]] = select(ReportCard).where(
        ReportCard.account_id == account_id
    )
    if owner_id is not None:
        stmt = stmt.where(ReportCard.owner_id == owner_id)
    if pet_id is not None:
        stmt = stmt.where(ReportCard.pet_id == pet_id)
    if date_from is not None:
        stmt = stmt.where(ReportCard.occurred_on >= date_from)
    if date_to is not None:
        stmt = stmt.where(ReportCard.occurred_on <= date_to)

    stmt = stmt.options(*_FRIEND_LOAD_OPTIONS).order_by(
        ReportCard.occurred_on.desc(), ReportCard.created_at.desc()
    )
    result = await session.execute(stmt)
    cards = result.scalars().unique().all()
    return [_card_to_read(card, s3_client=s3_client) for card in cards]
