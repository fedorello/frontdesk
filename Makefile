# Frontdesk — single entry point for common tasks. Run `make help`.
.DEFAULT_GOAL := help

API := apps/api
DASHBOARD := apps/dashboard
COMPOSE := docker compose -f deploy/docker/docker-compose.yml

.PHONY: help \
	install fmt fmt-check lint typecheck test test-integration check demo serve promote-admin \
	dashboard-install dashboard-check dashboard-e2e dashboard-dev \
	up down logs stack-build stack-up stack-down stack-logs

help: ## List available targets
	@awk 'BEGIN{FS=":.*?## "} \
		/^##@ /{printf "\n\033[1m%s\033[0m\n", substr($$0,5); next} \
		/^[a-zA-Z_-]+:.*?## /{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Backend (apps/api)
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

test-integration: ## Integration tests against a running Postgres (run `make up` first)
	cd $(API) && uv run pytest tests/integration --no-cov

check: fmt-check lint typecheck test ## The full backend gate

demo: ## Seed a demo business and book through the real stack (needs `make up` + FD_LLM_KEY)
	cd $(API) && uv run python scripts/demo.py

promote-admin: ## Grant admin to FRONTDESK_ADMIN_EMAILS accounts (idempotent; needs `make up`)
	cd $(API) && uv run python scripts/promote_admin.py

serve: ## Run the API locally with reload (needs `make up`)
	cd $(API) && uv run uvicorn frontdesk.interface.app:create_production_app --factory --reload

##@ Dashboard (apps/dashboard)
dashboard-install: ## Install the dashboard dependencies
	cd $(DASHBOARD) && pnpm install

dashboard-check: ## The dashboard gate (typecheck, lint, format, test, build)
	cd $(DASHBOARD) && pnpm typecheck && pnpm lint && pnpm fmt:check && pnpm test && pnpm build

dashboard-e2e: ## Dashboard end-to-end tests (Playwright)
	cd $(DASHBOARD) && pnpm e2e

dashboard-dev: ## Run the dashboard dev server
	cd $(DASHBOARD) && pnpm dev

##@ Local infrastructure (Postgres + Redis)
up: ## Start Postgres + Redis (for tests and local dev)
	$(COMPOSE) up -d

down: ## Stop everything (containers; keeps data)
	$(COMPOSE) down

logs: ## Tail infrastructure logs
	$(COMPOSE) logs -f

##@ Full stack in Docker (api + worker + dashboard)
stack-build: ## Build the app images
	$(COMPOSE) --profile app build

stack-up: ## Run the whole product (migrate → api + worker + dashboard)
	$(COMPOSE) --profile app up -d --build

stack-down: ## Stop the whole stack and remove its data volume
	$(COMPOSE) --profile app down -v

stack-logs: ## Tail the app logs
	$(COMPOSE) --profile app logs -f api worker dashboard
