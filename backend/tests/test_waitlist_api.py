"""Tests for waitlist offers, confirmations, and RBAC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, time
from typing import Any

import pytest
from httpx import AsyncClient

from app.services import waitlist_service

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_owner_with_pets(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    pet_names: list[str],
) -> tuple[str, list[str]]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Taylor",
            "last_name": "Client",
            "email": "taylor.client@example.com",
            "password": "OwnerPass1!",
        },
        headers=headers,
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_ids: list[str] = []
    for name in pet_names:
        pet_resp = await client.post(
            "/api/v1/pets",
            json={
                "owner_id": owner_id,
                "home_location_id": location_id,
                "name": name,
                "pet_type": "dog",
            },
            headers=headers,
        )
        assert pet_resp.status_code == 201
        pet_ids.append(pet_resp.json()["id"])
    return owner_id, pet_ids


def _build_reservation_payload(
    pet_id: str,
    location_id: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, Any]:
    start_dt = start or (datetime.now(UTC) + timedelta(days=1))
    end_dt = end or (start_dt + timedelta(days=3))
    return {
        "pet_id": pet_id,
        "location_id": location_id,
        "reservation_type": "boarding",
        "start_at": start_dt.isoformat(),
        "end_at": end_dt.isoformat(),
        "base_rate": "100.00",
        "status": "confirmed",
    }


async def _create_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> str:
    resp = await client.post("/api/v1/reservations", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_waitlist_requires_full_capacity(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_ids = await _create_owner_with_pets(
        client, headers, location_id, ["Rex"]
    )  # single pet

    waitlist_start_date = (datetime.now(UTC) + timedelta(days=7)).date()
    waitlist_end_date = waitlist_start_date + timedelta(days=1)

    waitlist_attempt = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": waitlist_start_date.isoformat(),
            "end_date": waitlist_end_date.isoformat(),
            "pets": [{"pet_id": pet_ids[0]}],
        },
        headers=headers,
    )
    assert waitlist_attempt.status_code == 400

    start_dt = datetime.combine(waitlist_start_date, time.min, tzinfo=UTC)
    end_dt = datetime.combine(
        waitlist_end_date + timedelta(days=1), time.min, tzinfo=UTC
    )
    reservation_id = await _create_reservation(
        client,
        headers,
        _build_reservation_payload(pet_ids[0], location_id, start=start_dt, end=end_dt),
    )

    waitlist_resp = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": waitlist_start_date.isoformat(),
            "end_date": waitlist_end_date.isoformat(),
            "pets": [{"pet_id": pet_ids[0]}],
            "notes": "Needs large run",
        },
        headers=headers,
    )
    assert waitlist_resp.status_code == 201
    entry_id = waitlist_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/reservations/{reservation_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(
        "/api/v1/waitlist",
        params={"limit": 10},
        headers=headers,
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["entries"][0]["id"] == entry_id


async def test_waitlist_offer_and_confirm_flow(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_ids = await _create_owner_with_pets(
        client, headers, location_id, ["Mochi", "Bean"]
    )

    waitlist_start_date = (datetime.now(UTC) + timedelta(days=10)).date()
    waitlist_end_date = waitlist_start_date + timedelta(days=2)

    # Ensure we can hold two reservations when offering
    rules_resp = await client.get(
        f"/api/v1/locations/{location_id}/capacity-rules",
        headers=headers,
    )
    assert rules_resp.status_code == 200
    boarding_rule = next(
        rule for rule in rules_resp.json() if rule["reservation_type"] == "boarding"
    )

    await client.patch(
        f"/api/v1/locations/{location_id}/capacity-rules/{boarding_rule['id']}",
        json={
            "max_active": 2,
            "waitlist_limit": boarding_rule.get("waitlist_limit"),
        },
        headers=headers,
    )

    start_dt = datetime.combine(waitlist_start_date, time.min, tzinfo=UTC)
    end_dt = datetime.combine(
        waitlist_end_date + timedelta(days=1), time.min, tzinfo=UTC
    )
    blocker_one = await _create_reservation(
        client,
        headers,
        _build_reservation_payload(pet_ids[0], location_id, start=start_dt, end=end_dt),
    )
    blocker_two = await _create_reservation(
        client,
        headers,
        _build_reservation_payload(pet_ids[1], location_id, start=start_dt, end=end_dt),
    )

    waitlist_resp = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": waitlist_start_date.isoformat(),
            "end_date": waitlist_end_date.isoformat(),
            "pets": [{"pet_id": pid} for pid in pet_ids],
            "priority": 5,
        },
        headers=headers,
    )
    assert waitlist_resp.status_code == 201
    entry_id = waitlist_resp.json()["id"]

    await client.delete(f"/api/v1/reservations/{blocker_one}", headers=headers)
    await client.delete(f"/api/v1/reservations/{blocker_two}", headers=headers)

    offer_resp = await client.post(
        f"/api/v1/waitlist/{entry_id}/offer",
        json={
            "hold_minutes": 240,
            "method": "email",
            "sent_to": "taylor.client@example.com",
        },
        headers=headers,
    )
    assert offer_resp.status_code == 200
    offer_body = offer_resp.json()
    assert len(offer_body["reservation_ids"]) == 2
    token_value = offer_body["token"]

    confirm_resp = await client.post(
        f"/api/v1/reservations/{offer_body['reservation_ids'][0]}/confirm",
        params={"token": token_value},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    repeat_resp = await client.post(
        f"/api/v1/reservations/{offer_body['reservation_ids'][0]}/confirm",
        params={"token": token_value},
    )
    assert repeat_resp.status_code == 200

    entry_detail = await client.get(
        "/api/v1/waitlist",
        params={"limit": 10},
        headers=headers,
    )
    assert entry_detail.status_code == 200
    entry_json = entry_detail.json()["entries"][0]
    assert entry_json["status"] == "converted"


async def test_waitlist_promote_and_expire(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_ids = await _create_owner_with_pets(
        client, headers, location_id, ["Scout"]
    )

    waitlist_start_date = (datetime.now(UTC) + timedelta(days=20)).date()
    waitlist_end_date = waitlist_start_date + timedelta(days=1)
    start_dt = datetime.combine(waitlist_start_date, time.min, tzinfo=UTC)
    end_dt = datetime.combine(
        waitlist_end_date + timedelta(days=1), time.min, tzinfo=UTC
    )

    blocker_id = await _create_reservation(
        client,
        headers,
        _build_reservation_payload(pet_ids[0], location_id, start=start_dt, end=end_dt),
    )

    waitlist_resp = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": waitlist_start_date.isoformat(),
            "end_date": waitlist_end_date.isoformat(),
            "pets": [{"pet_id": pet_ids[0]}],
        },
        headers=headers,
    )
    assert waitlist_resp.status_code == 201
    entry_id = waitlist_resp.json()["id"]

    await client.delete(f"/api/v1/reservations/{blocker_id}", headers=headers)

    promote_resp = await client.post(
        f"/api/v1/waitlist/{entry_id}/promote",
        json={},
        headers=headers,
    )
    assert promote_resp.status_code == 200
    promoted = promote_resp.json()[0]
    assert promoted["status"] == "confirmed"

    second_start_date = (datetime.now(UTC) + timedelta(days=25)).date()
    second_end_date = second_start_date + timedelta(days=1)
    second_start_dt = datetime.combine(second_start_date, time.min, tzinfo=UTC)
    second_end_dt = datetime.combine(
        second_end_date + timedelta(days=1), time.min, tzinfo=UTC
    )

    second_blocker_id = await _create_reservation(
        client,
        headers,
        _build_reservation_payload(
            pet_ids[0], location_id, start=second_start_dt, end=second_end_dt
        ),
    )

    second_waitlist = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": second_start_date.isoformat(),
            "end_date": second_end_date.isoformat(),
            "pets": [{"pet_id": pet_ids[0]}],
        },
        headers=headers,
    )
    assert second_waitlist.status_code == 201
    second_entry_id = second_waitlist.json()["id"]

    await client.delete(f"/api/v1/reservations/{second_blocker_id}", headers=headers)

    offer_resp = await client.post(
        f"/api/v1/waitlist/{second_entry_id}/offer",
        json={
            "hold_minutes": 5,
            "method": "email",
            "sent_to": "taylor.client@example.com",
        },
        headers=headers,
    )
    assert offer_resp.status_code == 200
    provisional_id = offer_resp.json()["reservation_ids"][0]

    sessionmaker = app_context["sessionmaker"]
    async with sessionmaker() as session:
        expired = await waitlist_service.expire_offers(
            session,
            account_id=account_id,
            now=datetime.now(UTC) + timedelta(minutes=10),
        )
    assert expired == 1

    entry_status = await client.get(
        "/api/v1/waitlist",
        params={"limit": 5},
        headers=headers,
    )
    assert entry_status.status_code == 200
    statuses = {item["id"]: item["status"] for item in entry_status.json()["entries"]}
    assert statuses[second_entry_id] == "expired"

    reservation_details = await client.get(
        f"/api/v1/reservations/{provisional_id}",
        headers=headers,
    )
    assert reservation_details.status_code == 200
    assert reservation_details.json()["status"] == "canceled"


async def test_waitlist_rbac_enforced(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    manager_token = await _authenticate(client, manager_email, manager_password)
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    owner_email = "pat.client@example.com"
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Pat",
            "last_name": "Client",
            "email": owner_email,
            "password": "OwnerPass1!",
        },
        headers=manager_headers,
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_resp = await client.post(
        "/api/v1/pets",
        json={
            "owner_id": owner_id,
            "home_location_id": location_id,
            "name": "Kona",
            "pet_type": "dog",
        },
        headers=manager_headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]

    owner_token = await _authenticate(client, owner_email, "OwnerPass1!")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    forbidden = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": (datetime.now(UTC) + timedelta(days=3)).date().isoformat(),
            "end_date": (datetime.now(UTC) + timedelta(days=4)).date().isoformat(),
            "pets": [{"pet_id": pet_id}],
        },
        headers=owner_headers,
    )
    assert forbidden.status_code == 403
