VENV?=backend/.venv
PYTHON:=$(VENV)/bin/python
PIP:=$(VENV)/bin/pip
RUFF:=$(VENV)/bin/ruff
MYPY:=$(VENV)/bin/mypy
PYTEST:=$(PYTHON) -m pytest

.PHONY: up down logs fmt lint type test seed seed-capacity seed-pricing

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

fmt:
	$(RUFF) format backend/app backend/tests

lint:
	$(RUFF) check backend/app backend/tests

type:
	$(MYPY) backend/app backend/tests

test:
	$(PYTEST)

seed:
	docker compose exec api python -m scripts.seed_capacity_rules

seed-capacity: seed

seed-pricing:
	docker compose exec api python -m scripts.seed_pricing
