SHELL := /bin/bash
.PHONY: setup check-node db migrate check-migrations dev api web seed samples test test-api test-web lint typecheck format build smoke verify reset-db
check-node:
	@python3 scripts/check_node.py

setup: check-node
	@test -f .env || cp .env.example .env
	uv sync --project apps/api --locked
	cd apps/web && npm ci

db:
	@command -v docker >/dev/null || (echo 'Docker is unavailable. Start a local PostgreSQL server, set DATABASE_URL in .env, then run make seed. See README Quick Start.'; exit 1)
	docker compose up -d --wait db

migrate:
	cd apps/api && uv run alembic upgrade head

check-migrations:
	cd apps/api && uv run python -m bottleiq.migrations

dev: check-node check-migrations
	python3 scripts/dev.py

api: check-migrations
	cd apps/api && uv run uvicorn bottleiq.main:app --reload --host 127.0.0.1 --port 8000

web: check-node
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

verify:
	uv run --project apps/api python scripts/verify_demo.py

reset-db:
	@test "$(CONFIRM)" = "yes" || (echo 'Destructive: run make reset-db CONFIRM=yes only for a disposable local database.'; exit 1)
	cd apps/api && uv run alembic downgrade base && uv run alembic upgrade head
	$(MAKE) seed
