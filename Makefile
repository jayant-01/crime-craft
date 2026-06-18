# Crime Craft — one-command developer ergonomics.
#
# Most hackathon flows: `make install && make seed && make dev`.
# Run `make` with no args to see the list.

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
VENV ?= venv
ACTIVATE = . $(VENV)/bin/activate

.DEFAULT_GOAL := help

.PHONY: help
help:  ## show this help
	@awk 'BEGIN{FS=":.*##"; printf "\nCrime Craft commands:\n\n"} \
	     /^[a-zA-Z_-]+:.*##/{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n"

# --- setup ----------------------------------------------------------------

.PHONY: venv
venv:  ## create the python venv (uses python3.12 by default)
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(ACTIVATE) && $(PIP) install --upgrade pip > /dev/null

.PHONY: install
install: venv  ## install backend (pip) and frontend (npm) deps
	@$(ACTIVATE) && $(PIP) install -r requirements.txt
	@cd apps/web && npm install
	@printf "\n\033[32m✓ installed\033[0m  next: \`make seed\` then \`make dev\`\n"

.PHONY: install-backend
install-backend: venv  ## install backend deps only
	@$(ACTIVATE) && $(PIP) install -r requirements.txt

.PHONY: install-frontend
install-frontend:  ## install frontend deps only
	@cd apps/web && npm install

# --- data -----------------------------------------------------------------

.PHONY: seed
seed:  ## load the sample CSV into the in-memory datastore + vector index
	@$(ACTIVATE) && $(PYTHON) -m services.ingest data/sample_cases.csv

.PHONY: reindex
reindex:  ## re-embed every case in the datastore (needed after switching to live RAG)
	@$(ACTIVATE) && $(PYTHON) -m services.rag.indexer reindex

.PHONY: train-recidivism
train-recidivism:  ## train the XGBoost recidivism model from current cases
	@$(ACTIVATE) && $(PYTHON) -m services.predictive.train

# --- run ------------------------------------------------------------------

.PHONY: dev
dev:  ## run backend + frontend in parallel (Ctrl+C exits both)
	@trap 'kill 0' EXIT; \
	  ($(ACTIVATE) && uvicorn main:app --reload --port 8000) & \
	  (cd apps/web && npm run dev) & \
	  wait

.PHONY: dev-backend
dev-backend:  ## run backend only (FastAPI on :8000)
	@$(ACTIVATE) && uvicorn main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend:  ## run frontend only (Vite on :5173)
	@cd apps/web && npm run dev

# --- test -----------------------------------------------------------------

.PHONY: test
test:  ## run the full pytest suite (offline, no API keys)
	@$(ACTIVATE) && $(PYTHON) -m pytest -v

.PHONY: test-fast
test-fast:  ## run tests, stop on first failure
	@$(ACTIVATE) && $(PYTHON) -m pytest -x -q

.PHONY: smoke
smoke:  ## quick health check — boot the app and hit /health
	@$(ACTIVATE) && $(PYTHON) -c "from fastapi.testclient import TestClient; from main import app; r = TestClient(app).get('/health'); assert r.status_code == 200, r.text; print('✓', r.json())"

# --- deploy ---------------------------------------------------------------

.PHONY: build-frontend
build-frontend:  ## build the React app for production (Catalyst client deploy)
	@cd apps/web && npm run build

.PHONY: catalyst-deploy
catalyst-deploy: build-frontend  ## deploy AppSail + frontend to Zoho Catalyst
	@cd catalyst && catalyst deploy

# --- housekeeping ---------------------------------------------------------

.PHONY: clean
clean:  ## remove pycache, .pyc, build artifacts (keeps venv)
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf apps/web/dist apps/web/.vite 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache 2>/dev/null || true
	@printf "\033[32m✓ cleaned\033[0m\n"

.PHONY: clean-all
clean-all: clean  ## also remove venv and node_modules (full reset)
	@rm -rf $(VENV) apps/web/node_modules
	@printf "\033[32m✓ full reset\033[0m  next: \`make install\`\n"
