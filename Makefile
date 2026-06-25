# Frontdesk — single entry point for common tasks. Run `make help`.
.DEFAULT_GOAL := help

API := apps/api
DASHBOARD := apps/dashboard
COMPOSE := docker compose -f deploy/docker/docker-compose.yml

.PHONY: help install fmt fmt-check lint typecheck test test-integration check demo \
	dashboard-install dashboard-check dashboard-e2e dashboard-dev up down logs

help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the API dependencies (uv)
	cd $(API) && uv sync

fmt: ## Format the API code
	cd $(API) && uv run ruff format .

fmt-check: ## Check formatting (no writes)
	cd $(API) && uv run ruff format --check .

lint: ## Lint + the hexagonal import contracts
	cd $(API) && uv run ruff check . && uv run lint-imports

typecheck: ## Static types (mypy --strict)
	cd $(API) && uv run mypy

test: ## Unit tests with coverage
	cd $(API) && uv run pytest

test-integration: ## Integration tests against a running Postgres (make up first)
	cd $(API) && uv run pytest tests/integration --no-cov

check: fmt-check lint typecheck test ## The full local gate

demo: ## Seed a demo business and book through the real stack (needs `make up` + FD_LLM_KEY)
	cd $(API) && uv run python scripts/demo.py

dashboard-install: ## Install the dashboard dependencies
	cd $(DASHBOARD) && pnpm install

dashboard-check: ## The dashboard gate (typecheck, lint, format, test, build)
	cd $(DASHBOARD) && pnpm typecheck && pnpm lint && pnpm fmt:check && pnpm test && pnpm build

dashboard-e2e: ## Dashboard end-to-end tests (Playwright)
	cd $(DASHBOARD) && pnpm e2e

dashboard-dev: ## Run the dashboard dev server
	cd $(DASHBOARD) && pnpm dev

up: ## Start infrastructure (PostgreSQL + Redis)
	$(COMPOSE) up -d

down: ## Stop infrastructure
	$(COMPOSE) down

logs: ## Tail infrastructure logs
	$(COMPOSE) logs -f
