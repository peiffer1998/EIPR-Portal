# Repository Guidelines

## Project Structure & Module Organization
- `backend/app/` contains the FastAPI stack (routers, services, models, schemas, integrations). Domain packages mirror the business areas: reservations, billing, notifications, capacity, etc.
- `backend/tests/` mirrors the module layout with pytest suites; place new tests beside the feature they exercise.
- `backend/alembic/versions/` stores database migrations. Use descriptive filenames and branch labels when required by a track.
- `backend/docs/` holds runbooks for each track (capacity, billing, ops). Add new guides here rather than editing `README.md` directly.

## Build, Test, and Development Commands
- `make up` or `docker compose up -d --build` launches the API with Postgres, Redis, Mailhog, and MinIO.
- `docker compose exec api alembic upgrade head` applies migrations inside the container; always run before feature testing.
- `.venv/bin/python -m pytest -q` (or `docker compose exec api pytest -q`) runs the full backend suite.
- `ruff check .`, `mypy .`, and `make fmt` keep formatting consistent; commits should be lint- and type-clean.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation. Modules/files use `snake_case`; classes use `PascalCase`; async service functions stay in `snake_case` with full type hints.
- Use `Decimal` for currency math, and prefer dependency helpers (`deps.get_db_session`, `deps.get_current_active_user`) over manual session management.
- When adding routers, append includes in `backend/app/api/v1/__init__.py` without reordering existing lines.

## Testing Guidelines
- Build fixtures with helpers from `backend/tests/conftest.py`. Name tests `test_<module>_<behavior>` and colocate service/API coverage.
- Deterministic dates (UTC) avoid timezone drift. Target ≥85% coverage as enforced by CI.
- Regenerate seed data or factories when adding migrations so tests remain idempotent.

## Commit & Pull Request Guidelines
- Follow the `type(scope): summary` convention (e.g., `feat(reservations): lifecycle transitions`). Keep each checklist step as a focused commit.
- Document migrations, seeds, and new endpoints in PR descriptions. Include curl examples or screenshots whenever responses/UI change.
- Before pushing, verify `ruff`, `mypy`, and `pytest` locally; CI expects a clean run.

## Security & Configuration Tips
- Store secrets in `.env` variants; never commit live credentials. Local `.env.example` already lists required keys.
- Enforce role checks via the auth dependencies and ensure audit events capture actor, IP, and action for sensitive mutations.
