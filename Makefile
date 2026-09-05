UV ?= uv
DOCKER_COMPOSE ?= docker compose

.PHONY: install sync dev lint lint-fix format format-check typecheck architecture/imports test test-all test-cov \
	pre-commit-install pre-commit check db-up migrate seed-catalog db-down

install: sync

sync:
	$(UV) sync

dev:
	$(UV) run fastapi dev src/api/main.py --host 127.0.0.1 --port 8000

lint:
	$(UV) run ruff check .

lint-fix:
	$(UV) run ruff check . --fix

format:
	$(UV) run ruff format .

format-check:
	$(UV) run ruff format --check .

typecheck:
	$(UV) run mypy .
	$(UV) run pyright

architecture/imports:
	$(UV) run lint-imports

test:
	$(UV) run pytest -m "not integration and not e2e"

test-all:
	$(UV) run pytest

test-cov:
	$(UV) run pytest -m "not integration and not e2e" --cov=src --cov-branch --cov-report=term-missing

pre-commit-install:
	$(UV) run pre-commit install

pre-commit:
	$(UV) run pre-commit run --all-files

check: format-check lint typecheck architecture/imports test

db-up:
	$(DOCKER_COMPOSE) up -d --wait mysql

migrate:
	$(UV) run alembic upgrade head

seed-catalog:
	$(UV) run python -m scripts.seed_catalog --textbooks 2 --chapters-per-textbook 5

db-down:
	$(DOCKER_COMPOSE) down --volumes
