.PHONY: help demo-up demo-down test test-unit test-integration test-golden \
        lint purity-check vocab-lint migrate seed-demo seed-users \
        verify-endpoints verify-ledger build-ml docs-serve

PYTHON := python
COMPOSE := docker compose
PROJECT := dummy-sih26015

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── DOCKER LIFECYCLE ───────────────────────────────────────────────────────
demo-up: ## Spin up full demo stack (Postgres, Redis, MinIO, API, Workers, Frontend)
	$(COMPOSE) up -d --build
	@echo "Waiting for services to be healthy..."
	@sleep 10
	$(MAKE) migrate
	$(MAKE) seed-demo
	$(MAKE) seed-users
	@echo ""
	@echo "✅  Stack is live!"
	@echo "   Dashboard  → http://localhost:5173"
	@echo "   API Docs   → http://localhost:8000/docs"
	@echo "   MinIO UI   → http://localhost:9001"

demo-down: ## Tear down demo stack
	$(COMPOSE) down -v --remove-orphans

demo-restart: demo-down demo-up ## Fresh restart

logs: ## Tail all container logs
	$(COMPOSE) logs -f

logs-api: ## Tail API logs only
	$(COMPOSE) logs -f api

logs-worker: ## Tail Celery worker logs
	$(COMPOSE) logs -f worker

# ─── DATABASE ───────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	$(COMPOSE) exec api alembic -c /app/db/alembic.ini upgrade head

migrate-gen: ## Generate new migration (NAME=<migration-name>)
	$(COMPOSE) exec api alembic -c /app/db/alembic.ini revision --autogenerate -m "$(NAME)"

migrate-down: ## Rollback last migration
	$(COMPOSE) exec api alembic -c /app/db/alembic.ini downgrade -1

# ─── SEEDING ────────────────────────────────────────────────────────────────
seed-demo: ## Seed Nanded district demo data (real Sentinel-2 epochs)
	$(COMPOSE) exec api $(PYTHON) /app/scripts/seed_demo.py

seed-users: ## Seed multi-role test users
	$(COMPOSE) exec api $(PYTHON) /app/scripts/seed_users.py

seed-golden: ## Seed all 18 golden test cases
	$(COMPOSE) exec api $(PYTHON) /app/scripts/seed_golden.py

# ─── TESTING ────────────────────────────────────────────────────────────────
test: test-unit test-integration test-golden ## Run full test suite

test-unit: ## Run unit tests (pure engine + AST purity checks)
	cd backend && $(PYTHON) -m pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests against live API
	cd backend && $(PYTHON) -m pytest tests/integration/ -v --tb=short

test-golden: ## Run 18-case golden test suite
	cd backend && $(PYTHON) -m pytest tests/golden/ -v --tb=short

# ─── CODE QUALITY ────────────────────────────────────────────────────────────
lint: ## Run ruff linter + mypy type checker
	cd backend && ruff check app/ && mypy app/

purity-check: ## AST-check that engine modules have zero IO
	cd backend && $(PYTHON) -m pytest tests/unit/test_wii_purity.py tests/unit/test_crossval_purity.py -v

vocab-lint: ## Ethics vocabulary linter (no accusatory language)
	$(PYTHON) scripts/vocabulary_lint.py

fmt: ## Auto-format with ruff
	cd backend && ruff format app/

# ─── VERIFICATION SCRIPTS ───────────────────────────────────────────────────
verify-endpoints: ## Test live govt/Sentinel API endpoints → docs/api-health.md
	$(PYTHON) scripts/verify_endpoints.py

verify-ledger: ## Verify adjudication ledger hash-chain integrity
	$(PYTHON) scripts/verify_ledger.py

# ─── ML ─────────────────────────────────────────────────────────────────────
build-ml: ## Train + quantize CV structure classifier
	cd ml/classifier && $(PYTHON) train.py

export-tflite: ## Export trained model to TFLite
	cd ml/classifier && $(PYTHON) export_tflite.py

# ─── FRONTEND ───────────────────────────────────────────────────────────────
frontend-dev: ## Run Vite dev server
	cd frontend && npm run dev

frontend-build: ## Production build
	cd frontend && npm run build

# ─── DOCUMENTATION ──────────────────────────────────────────────────────────
docs-serve: ## Serve MkDocs locally
	mkdocs serve

render-math: ## Re-render WII formula tables in docs from engine source
	$(PYTHON) scripts/render_math_tables.py

# ─── QUICK HEALTH ───────────────────────────────────────────────────────────
status: ## Show container status
	$(COMPOSE) ps

health: ## Quick health check
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not responding"
