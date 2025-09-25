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

## Docker Compose Quick Start

```bash
cp .env.example .env
pre-commit install
make up
# Once containers are running:
docker compose exec api alembic upgrade head
docker compose exec api pytest -q
```

Use `make down` to stop containers and `make logs` to tail the API service.

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

| Variable | Description |
| --- | --- |
| `APP_ENV` | Runtime mode for the API (e.g. `local`, `staging`, `production`). |
| `SECRET_KEY` | Secret used for signing session data or legacy integrations. |
| `DATABASE_URL` | Async database DSN for application writes (used by SQLAlchemy). |
| `SYNC_DATABASE_URL` | Sync DSN for tooling such as Alembic migrations. |
| `REDIS_URL` | Redis connection string for caching and background jobs. |
| `SMTP_HOST` | SMTP host for transactional email delivery. |
| `SMTP_PORT` | SMTP port. |
| `SMTP_USER` | SMTP username credential (if required). |
| `SMTP_PASSWORD` | SMTP password credential (if required). |
| `SMTP_FROM` | Default from address for outbound email. |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key for payment forms. |
| `STRIPE_SECRET_KEY` | Stripe secret key for server-side payment actions. |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret. |
| `STRIPE_TERMINAL_LOCATION` | Stripe Terminal location ID for WisePOS devices. |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for SMS. |
| `TWILIO_AUTH_TOKEN` | Twilio auth token for SMS. |
| `TWILIO_MESSAGING_SERVICE_SID` | Twilio messaging service SID for SMS campaigns. |
| `JWT_SECRET_KEY` | Secret used for JWT signing. |
| `JWT_ALGORITHM` | JWT signing algorithm (e.g. `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes. |
| `S3_ENDPOINT_URL` | Object storage endpoint (MinIO or AWS S3). |
| `S3_BUCKET` | Bucket name for media uploads. |
| `S3_ACCESS_KEY_ID` | Object storage access key. |
| `S3_SECRET_ACCESS_KEY` | Object storage secret key. |
| `QBO_EXPORT_DIR` | Directory for QuickBooks export files inside the container. |
| `KISI_API_KEY` | Kisi API key for door integrations. |
| `KISI_DOOR_ID` | Kisi door identifier for access control. |

See `.env.example` for sample values.
