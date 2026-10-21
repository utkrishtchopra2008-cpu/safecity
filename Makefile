
.PHONY: env setup db-up db-down dev-backend dev-frontend test-backend lint-backend format-backend format-backend-check typecheck-backend lint-frontend format-frontend typecheck-frontend test-frontend build-frontend check

# Copy local placeholders once. Edit .env locally; never commit it.
env:
	@test -f .env || cp .env.example .env

setup:
	uv sync --project backend --group dev
	npm --prefix frontend install

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

dev-backend:
	uv run --project backend uvicorn app.main:app --app-dir backend --reload --env-file .env

dev-frontend:
	npm --prefix frontend run dev

test-backend:
	cd backend && uv run pytest

lint-backend:
	cd backend && uv run ruff check app tests migrations

format-backend:
	cd backend && uv run ruff format app tests migrations

format-backend-check:
	cd backend && uv run ruff format --check app tests migrations

typecheck-backend:
	cd backend && uv run mypy app

lint-frontend:
	npm --prefix frontend run lint

format-frontend:
	npm --prefix frontend run format:check

typecheck-frontend:
	npm --prefix frontend run typecheck

test-frontend:
	npm --prefix frontend run test:run

build-frontend:
	npm --prefix frontend run build

check: lint-backend format-backend-check typecheck-backend test-backend lint-frontend format-frontend typecheck-frontend test-frontend build-frontend
