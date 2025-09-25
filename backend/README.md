# Eastern Iowa Pet Resort Backend

FastAPI-based backend service for managing reservations, operations, billing, and communications for the Eastern Iowa Pet Resort platform.

## Getting Started

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Define environment variables in a `.env` file. See `.env.example` for required settings.
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Layout

- `app/` – application package (API routers, services, models, schemas).
- `tests/` – automated tests.
- `pyproject.toml` – dependency and build configuration.

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
