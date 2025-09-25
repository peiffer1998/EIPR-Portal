# Repository Guidelines

## Project Structure & Module Organization
- `backend/app/` contains FastAPI services, routers, schemas, and SQLAlchemy models. Keep domain code in feature folders (e.g., `services`, `api/v1`, `models`).
- `backend/tests/` hosts pytest suites; mirror the runtime package layout when adding coverage.
- Infrastructure assets (Dockerfile, `docker-compose.yml`, Makefile, `.env.example`) live at the repo root; documentation lives under `backend/docs/`.

## Build, Test, and Development Commands
- `make up` spins up the full Docker compose stack (API, Postgres, Redis, Mailhog, MinIO).
- `make down` stops and removes containers; run before rebuilding images.
- `backend/.venv/bin/python -m pytest -q` executes the full automated test suite locally.
- `backend/.venv/bin/ruff check backend` and `backend/.venv/bin/mypy --ignore-missing-imports app tests` lint and type-check the backend.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; rely on `ruff` and `black` for formatting fixes.
- Prefer explicit module paths (e.g., `from app.services import ...`) and snake_case filenames; models use PascalCase names.
- Commit to async SQLAlchemy patterns (`async def`, `AsyncSession`) throughout API layers.

## Testing Guidelines
- Use pytest with `asyncio` fixtures; name files `test_*.py` and functions `test_*` mirroring feature modules.
- Maintain green coverage for suites under `backend/tests/`; add regression tests for every new route, service, or migration.
- For database migrations, run `PYTHONPATH=. backend/.venv/bin/alembic upgrade head` once the Postgres service is available.

## Commit & Pull Request Guidelines
- Follow the existing Conventional Commit style (`feat(scope): summary`, `chore(...)`, `ci(...)`).
- One logical change per commit; include migrations and tests in the same commit when they relate.
- Pull requests should describe motivation, list testing commands executed, and reference any tracking issues. Attach screenshots for UI/portal updates when applicable.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets. Override `DATABASE_URL`/`SECRET_KEY` with secure values in non-local environments.
- Use the synchronous `SYNC_DATABASE_URL` for Alembic migrations; runtime services rely on the async DSN (`DATABASE_URL`).
