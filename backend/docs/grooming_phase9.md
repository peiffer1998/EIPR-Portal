# Grooming Phase 9 Usage Guide

## Create a Specialist and Schedule
1. Authenticate as a staff user and obtain a bearer token.
2. `POST /api/v1/grooming/specialists` with name, location, commission settings.
3. `POST /api/v1/grooming/specialists/{id}/schedules` to add weekly blocks.
4. Optional `POST /api/v1/grooming/specialists/{id}/time-off` for breaks or PTO.

## Configure Services and Add-ons
- `POST /api/v1/grooming/services` to define base duration and price.
- `POST /api/v1/grooming/addons` for optional upgrades that add duration/price.

## Find Availability and Book
1. Query `GET /api/v1/grooming/availability` with date range, location, service, and optional add-ons/specialist filters.
2. Book using `POST /api/v1/grooming/appointments` (owner, pet, specialist, service, add-ons, start time).
3. Reschedule via `PATCH /api/v1/grooming/appointments/{id}/reschedule`.
4. Update status or cancel using the `/status` and `/cancel` endpoints.

## Reporting
- Daily load: `GET /api/v1/grooming/reports/load?report_date=YYYY-MM-DD`.
- Commission totals: `GET /api/v1/grooming/reports/commissions?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`.

## Smoke Validation
- `ruff check .`
- `mypy .`
- `pytest -q`
