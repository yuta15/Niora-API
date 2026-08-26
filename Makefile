UV ?= uv

.PHONY: install sync lint lint-fix format format-check typecheck architecture/imports test test-all test-cov \
	pre-commit-install pre-commit check

install: sync

sync:
	$(UV) sync

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
