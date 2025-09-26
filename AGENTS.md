# Repository Guidelines

## Project Structure & Module Organization
- `backend/app/` holds the FastAPI application (routers, services, models, schemas) and domain modules like reservations, billing, and notifications.
- `backend/tests/` mirrors the app modules with pytest suites; add new tests beside the code they exercise.
- `backend/alembic/` contains database migrations; place new revisions under `versions/` with descriptive filenames.
- `docs/` captures operational guides (capacity, billing, ops tracks). Create new track docs here when adding features.

## Build, Test, and Development Commands
- `make up` / `docker compose up -d --build` starts the full stack (API, Postgres, Redis, Mailhog, MinIO).
- `docker compose exec api alembic upgrade head` applies the latest migrations inside the container.
- `.venv/bin/python -m pytest -q` or `docker compose exec api pytest -q` runs the backend test suite.
- `ruff check .` and `mypy .` must be clean before every commit; `make fmt` auto-formats with ruff/black.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation. Keep modules and files in `snake_case`, classes in `PascalCase`, and functions/variables in `snake_case`.
- All new modules require type hints. Use `Decimal` for currency and prefer dependency-injected services over direct imports.
- When expanding routers, register them in `backend/app/api/v1/__init__.py` without reordering existing includes.

## Testing Guidelines
- Use pytest with factory fixtures from `backend/tests/conftest.py`. Name tests `test_<module>_<behavior>`.
- Include both service-level and API-level tests when adding endpoints. Seed deterministic data in fixtures to avoid timezone drift.
- Target coverage ≥85% as enforced by CI; add regression tests for every bug fix.

## Commit & Pull Request Guidelines
- Commit messages follow the `type(scope): summary` pattern seen in history (e.g., `feat(reservations): waitlist promote flow`).
- Keep commits scoped to a checklist step; run lint, type check, and tests before committing.
- PRs should describe the feature, testing performed, migrations added, and any follow-up tasks; attach screenshots or curl snippets when UI/response changes apply.

## Security & Configuration Tips
- Store secrets in `.env` variants; never commit real keys. Use provided Mailhog, MinIO, and Stripe test credentials for local runs.
- Enforce role checks via `get_current_active_user` dependencies. Audit events must capture actor, action, and IP for sensitive mutations.
