SHELL := /bin/bash
.PHONY: setup db migrate dev api web seed samples test test-api test-web lint typecheck format build smoke reset-db
setup:
	@test -f .env || cp .env.example .env
	uv sync --project apps/api --locked
	cd apps/web && npm ci

db:
	docker compose up -d --wait db

migrate:
	cd apps/api && uv run alembic upgrade head

dev:
	python3 scripts/dev.py

api:
	cd apps/api && uv run uvicorn bottleiq.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm run dev

seed: migrate
	cd apps/api && uv run python -m bottleiq.seed

samples:
	cd apps/api && uv run python -m bottleiq.seed --samples ../../data/samples

test: test-api test-web

test-api:
	cd apps/api && uv run pytest -q

test-web:
	cd apps/web && npm test

lint:
	cd apps/api && uv run ruff check bottleiq tests alembic && uv run ruff format --check bottleiq tests alembic
	cd apps/web && npm run lint && npm run format:check

typecheck:
	cd apps/api && uv run mypy bottleiq
	cd apps/web && npm run typecheck

format:
	cd apps/api && uv run ruff check --fix bottleiq tests alembic && uv run ruff format bottleiq tests alembic
	cd apps/web && npm run format

build:
	cd apps/web && npm run build

smoke:
	cd apps/web && npm run test:e2e

reset-db:
	@test "$(CONFIRM)" = "yes" || (echo 'Destructive: run make reset-db CONFIRM=yes only for a disposable local database.'; exit 1)
	cd apps/api && uv run alembic downgrade base && uv run alembic upgrade head
	$(MAKE) seed
