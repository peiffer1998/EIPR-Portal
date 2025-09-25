"""Seed default capacity rules for all locations."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.location import Location
from app.models.location_capacity import LocationCapacityRule
from app.models.reservation import ReservationType

DEFAULT_MAX_ACTIVE = 20
DEFAULT_WAITLIST_LIMIT = 10


async def seed_capacity(default_max: int = DEFAULT_MAX_ACTIVE, waitlist: int = DEFAULT_WAITLIST_LIMIT) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        locations: Iterable[Location] = (await session.execute(select(Location))).scalars()
        created = 0
        for location in locations:
            for reservation_type in ReservationType:
                existing = await session.execute(
                    select(LocationCapacityRule).where(
                        LocationCapacityRule.location_id == location.id,
                        LocationCapacityRule.reservation_type == reservation_type,
                    )
                )
                if existing.scalar_one_or_none() is None:
                    session.add(
                        LocationCapacityRule(
                            location_id=location.id,
                            reservation_type=reservation_type,
                            max_active=default_max,
                            waitlist_limit=waitlist,
                        )
                    )
                    created += 1
        if created:
            await session.commit()
        print(f"Seeded {created} capacity rule(s).")


def main() -> None:
    asyncio.run(seed_capacity())


if __name__ == "__main__":
    main()
