# Eastern Iowa Pet Resort Backend

FastAPI-based backend service for managing reservations, operations, billing, and communications for the Eastern Iowa Pet Resort platform.

## Getting Started

1. Create and activate a Python 3.11+ virtual environment (e.g., `python3 -m venv .venv && source .venv/bin/activate`).
2. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Define environment variables in a `.env` file. See `.env.example` for required settings.
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running Tests

With the virtual environment active, install dev dependencies and execute the suite:

```bash
pip install -e .[dev]
pytest
```

## Database Migrations

Run Alembic migrations whenever the schema changes:

```bash
alembic upgrade head
```

To create a new revision:

```bash
alembic revision --autogenerate -m "describe change"
```

## Seeding Capacity Defaults

Seed default capacity rules for all locations (idempotent):

```bash
python -m scripts.seed_capacity_rules
```

## Project Layout

- `app/` – application package (API routers, services, models, schemas).
- `tests/` – automated tests.
- `pyproject.toml` – dependency and build configuration.

## Feature Highlights

- **Staff onboarding** – invite staff, manage roles/status, and accept invitations via `/api/v1/users/invitations` and `/api/v1/auth/invitations/accept`.
- **Background notifications** – email/SMS stubs send booking, check-in, invoice, payment, and password reset updates without blocking API responses.
- **Analytics** – `/api/v1/reports/occupancy` and `/api/v1/reports/revenue` provide capacity and financial reporting for staff roles.
- **Service catalog & packages** – manage services, retail items, and multi-use packages with `/api/v1/service-items` and `/api/v1/packages`.
- **Waitlists & scheduling** – capture overflow demand through `/api/v1/waitlist` and maintain operating hours/closures under `/api/v1/locations/{location_id}/hours|closures`.
- **Document metadata** – attach vaccination or policy documents to owners/pets via `/api/v1/documents`.

## Migration History

Recent revisions of note:

- `0007_staff_invitations` – adds staff invitation workflow tables.
- `0008_service_extensions` – adds service catalog, packages, waitlists, location hours/closures, and document metadata.

Apply migrations with `alembic upgrade head` after pulling updates.

## Tooling

- Formatting & linting: `ruff`
- Static typing: `mypy`
- Testing: `pytest`, `pytest-asyncio`
- API server: `uvicorn`

## Environment Variables

Set the following variables for local development:

- `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

See `.env.example` for defaults.
