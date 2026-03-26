SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

ifneq (,$(wildcard .env))
include .env
export
endif

REPO_ROOT := $(CURDIR)
APP_ROOT := $(REPO_ROOT)
UV ?= $(or $(shell command -v uv 2>/dev/null),$(HOME)/.local/bin/uv)
UV_RUN := $(UV) run --project $(REPO_ROOT)
RUFF := $(UV_RUN) ruff
PRE_COMMIT := $(UV_RUN) pre-commit
PYTHON := $(UV_RUN) python
LOCAL_TZ ?= UTC
DATE ?= $(if $(RUN_DATE),$(RUN_DATE),$(shell TZ=$(LOCAL_TZ) date +%F))
SOURCES ?= 20minutos abc eldiario elmundo elpais lavanguardia
SOURCE ?=
OUT_PREFIX ?= manual
DATABASE_URL ?=
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
SCHEDULER_SCRIPT := scripts/run_scheduled.sh
VAR_ROOT := var
LOCK_DIR := $(VAR_ROOT)/lock
LOG_DIR := $(VAR_ROOT)/log
STATE_DIR := $(VAR_ROOT)/state
COMPOSE_FILE ?= compose.yaml
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE)
LOCAL_DB_SERVICE ?= postgres
LOCAL_DB_HOST ?= 127.0.0.1
LOCAL_DB_PORT ?= 5433
LOCAL_DB_NAME ?= spain_news_bias
LOCAL_DB_USER ?= spain_news
LOCAL_DB_PASSWORD ?= spain_news_dev
LOCAL_DATABASE_URL := postgresql+psycopg://$(LOCAL_DB_USER):$(LOCAL_DB_PASSWORD)@$(LOCAL_DB_HOST):$(LOCAL_DB_PORT)/$(LOCAL_DB_NAME)

.PHONY: help print-app-root preflight sync pre-commit lint check test docs-build docs-serve frontend-install frontend-build frontend-check smoke run-source run-source-persist run-all run-all-persist api analysis-db-init build-matching-corpus enrich-articles analyze-editorial analyze-editorial-failed build-story-clusters story-cluster-report semantic-db-init semantic-sync semantic-project semantic-neighbors semantic-build semantic-smoke scheduler-once scheduler-dry-run stories-refresh-once explorer-refresh-once full-refresh-once status tail-log verify-output verify-db db-url db-up db-down db-logs db-psql db-check clean-state

help:
	@printf '%s\n' \
	  'Root app + operator surface for spain-news-bias-scraper' \
	  '' \
	  'Bootstrap:' \
	  '  make sync                     Create/update the uv-managed environment' \
	  '  make preflight                Check uv/runtime wiring' \
	  '  make lint                     Run ruff using the managed environment' \
	  '  make pre-commit               Run repo hooks (ruff-check + ruff-format)' \
	  '  make check                    Canonical local gate: pre-commit + tests' \
	  '  make test                     Run tests from repo root' \
  '  make docs-build               Build the MkDocs site into site/' \
  '  make docs-serve               Serve the MkDocs site locally' \
  '  make frontend-install         Install frontend dependencies' \
  '  make frontend-build           Build the frontend app' \
  '  make frontend-check           Install deps, then build the frontend app' \
	  '' \
	  'Runtime:' \
	  '  make smoke SOURCE=elpais      Quick non-persistent scrape' \
	  '  make run-source SOURCE=...    Run one source for DATE=$(DATE)' \
	  '  make run-source-persist SOURCE=... DATABASE_URL=postgresql+psycopg://...' \
	  '  make run-all                  Run all sources sequentially without persistence' \
	  '  make run-all-persist          Run all sources sequentially with persistence' \
	  '  make api DATABASE_URL=...     Run FastAPI app via uvicorn' \
	  '  make analysis-db-init DATABASE_URL=...           Create analysis/enrichment tables + seed taxonomy' \
	  '  make build-matching-corpus DATABASE_URL=...      Build the derived hard-news matching corpus' \
	  '  make enrich-articles DATABASE_URL=...            Enrich recent persisted articles (OpenRouter optional)' \
	  '  make analyze-editorial DATABASE_URL=...          Run dedicated LLM editorial analysis for recent articles' \
	  '  make analyze-editorial-failed DATABASE_URL=...   Re-run failed editorial analysis for recent articles' \
	  '  make build-story-clusters DATABASE_URL=...       Rebuild bounded same-story clusters' \
	  '  make story-cluster-report DATABASE_URL=...       Print recent cluster summaries' \
	  '  make semantic-db-init DATABASE_URL=...           Create pgvector extension + semantic tables' \
	  '  make semantic-sync DATABASE_URL=... LIMIT=100    Backfill/sync missing or changed embeddings' \
	  '  make semantic-project DATABASE_URL=...           Rebuild the named explorer projection set (defaults to pca_3d_latest)' \
	  '  make semantic-neighbors DATABASE_URL=... ARTICLE_ID=...  Query nearest neighbors' \
	  '  make semantic-build DATABASE_URL=... LIMIT=500   Export semantic artifacts from persisted state' \
	  '  make semantic-smoke DATABASE_URL=...             Export a bounded semantic smoke artifact set' \
	  '' \
	  'Scheduler + verification:' \
	  '  make scheduler-dry-run        Show LEGACY scrape-only execution plan (prefer stories-refresh-once)' \
	  '  make scheduler-once           Run the LEGACY scrape-only wrapper once (prefer stories-refresh-once)' \
	  '  make stories-refresh-once     Run scrape + analysis + clustering refresh once' \
	  '  make explorer-refresh-once    Run semantic explorer refresh once' \
	  '  make full-refresh-once        Run stories refresh, then explorer refresh' \
	  '  make status                   Show LEGACY scheduler state files' \
	  '  make tail-log                 Tail LEGACY scheduler log' \
	  '  make verify-output            Check expected JSON/metrics files for DATE' \
	  '  make verify-db DATABASE_URL=postgresql+psycopg://...  Check article row count' \
	  '' \
	  'Optional local DB:' \
	  '  make db-url                   Print the local dev DATABASE_URL' \
	  '  make db-up                    Start optional local Postgres via Docker Compose' \
	  '  make db-down                  Stop optional local Postgres' \
	  '  make db-logs                  Tail local Postgres logs' \
	  '  make db-psql                  Open psql inside the local Postgres container' \
	  '  make db-check                 Wait for local Postgres readiness' \
	  '' \
	  'Notes:' \
	  '  - Repo root is the canonical app root.' \
	  '  - The authoritative Python workflow is uv sync + uv run ...' \
	  '  - Repo root is the only supported app root; tests use fixtures under tests/fixtures/evidence.'

print-app-root:
	@printf '%s\n' "$(APP_ROOT)"

sync:
	@$(UV) sync

preflight:
	@set -euo pipefail; \
	mkdir -p "$(LOCK_DIR)" "$(LOG_DIR)" "$(STATE_DIR)" "data"; \
	printf 'app_root=%s\n' "$(APP_ROOT)"; \
	command -v "$(UV)" >/dev/null || { echo 'uv missing'; exit 1; }; \
	[[ -f "$(APP_ROOT)/src/main.py" ]] || { echo 'src/main.py missing under repo root'; exit 1; }; \
	if [[ -z "$(DATABASE_URL)" ]]; then echo 'warning: DATABASE_URL not set; persist/api targets will fail until you provide it'; fi; \
	if ! command -v docker >/dev/null 2>&1; then echo 'warning: docker not found; host-based mode is the intended default'; fi; \
	if ! command -v flock >/dev/null 2>&1; then echo 'warning: flock not found; scheduler wrappers that rely on file locks may not work on this host'; fi; \
	PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) -m src.main --help >/dev/null; \
	echo 'python entrypoint ok'

lint: preflight
	@PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(RUFF) check src tests scripts

pre-commit: preflight
	@cd "$(APP_ROOT)" && $(PRE_COMMIT) run --all-files

check: pre-commit test

test: preflight
	@cd "$(APP_ROOT)" && \
	PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) -m pytest -q tests

docs-build: preflight
	@cd "$(APP_ROOT)" && $(PYTHON) -m mkdocs build --strict

docs-serve: preflight
	@cd "$(APP_ROOT)" && $(PYTHON) -m mkdocs serve -a 127.0.0.1:8001

frontend-install:
	@cd "$(APP_ROOT)/frontend" && npm install --include=dev

frontend-build:
	@cd "$(APP_ROOT)/frontend" && npm run build

frontend-check: frontend-install frontend-build

smoke: preflight
	@$(MAKE) --no-print-directory run-source SOURCE="$(if $(SOURCE),$(SOURCE),elpais)" DATE="$(DATE)" OUT_PREFIX=smoke MAX_DISCOVERY_URLS=20 MAX_ARTICLES_TO_EXTRACT=10 MAX_RUNTIME_SECONDS=45

run-source: preflight
	@set -euo pipefail; \
	[[ -n "$(SOURCE)" ]] || { echo 'SOURCE is required'; exit 1; }; \
	mkdir -p "$(APP_ROOT)/data" "$(APP_ROOT)/logs"; \
	cmd=( $(PYTHON) -m src.main --source "$(SOURCE)" --date "$(DATE)" --out "data/$(OUT_PREFIX)_$(SOURCE)_$(DATE).json" --metrics-out "logs/$(OUT_PREFIX)_$(SOURCE)_$(DATE)_metrics.json" --max-discovery-urls "$${MAX_DISCOVERY_URLS:-300}" --max-articles-to-extract "$${MAX_ARTICLES_TO_EXTRACT:-120}" --max-runtime-seconds "$${MAX_RUNTIME_SECONDS:-180}" ); \
	if [[ "$${PERSIST:-0}" == 1 ]]; then \
	  [[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for persistence'; exit 1; }; \
	  cmd+=( --persist --db-url "$(DATABASE_URL)" ); \
	fi; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" "$${cmd[@]}"

run-source-persist:
	@$(MAKE) --no-print-directory run-source SOURCE="$(SOURCE)" DATE="$(DATE)" OUT_PREFIX="$(OUT_PREFIX)" PERSIST=1 DATABASE_URL="$(DATABASE_URL)"

run-all: preflight
	@set -euo pipefail; \
	for source in $(SOURCES); do \
	  echo "==> $$source $(DATE)"; \
	  $(MAKE) --no-print-directory run-source SOURCE="$$source" DATE="$(DATE)" OUT_PREFIX="$(OUT_PREFIX)"; \
	done

run-all-persist: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for persistence'; exit 1; }; \
	for source in $(SOURCES); do \
	  echo "==> $$source $(DATE) persist"; \
	  $(MAKE) --no-print-directory run-source SOURCE="$$source" DATE="$(DATE)" OUT_PREFIX="$(OUT_PREFIX)" PERSIST=1 DATABASE_URL="$(DATABASE_URL)"; \
	done

api: preflight
	@[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for api'; exit 1; }
	@cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) -m uvicorn src.api.app:create_app --factory --host "$(API_HOST)" --port "$(API_PORT)"

analysis-db-init: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for analysis-db-init'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/init_analysis_schema.py --db-url "$(DATABASE_URL)"

enrich-articles: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for enrich-articles'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/enrich_articles.py --db-url "$(DATABASE_URL)" --days-back "$${DAYS_BACK:-2}" --limit "$${LIMIT:-150}" --corpus "$${CORPUS:-matching}"

build-matching-corpus: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for build-matching-corpus'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/build_matching_corpus.py --db-url "$(DATABASE_URL)" --days-back "$${DAYS_BACK:-3}" --daily-cap "$${DAILY_CAP:-0}" --audit-out "$${AUDIT_OUT:-data/matching_audit_$(DATE).json}"

analyze-editorial: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for analyze-editorial'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/analyze_editorial.py --db-url "$(DATABASE_URL)" --days-back "$${DAYS_BACK:-2}" --limit "$${LIMIT:-100}" $${REPROCESS:+--reprocess}

analyze-editorial-failed: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for analyze-editorial-failed'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/analyze_editorial.py --db-url "$(DATABASE_URL)" --days-back "$${DAYS_BACK:-3}" --limit "$${LIMIT:-50}" --failed-only

build-story-clusters: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for build-story-clusters'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/build_story_clusters.py --db-url "$(DATABASE_URL)" --days-back "$${DAYS_BACK:-3}" --limit "$${LIMIT:-200}" --score-threshold "$${SCORE_THRESHOLD:-0.55}" --corpus "$${CORPUS:-matching}"

story-cluster-report: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for story-cluster-report'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/story_cluster_report.py --db-url "$(DATABASE_URL)" --limit "$${LIMIT:-20}"

semantic-db-init: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-db-init'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/init_pgvector.py --db-url "$(DATABASE_URL)" $${SEMANTIC_ARGS:-}

semantic-sync: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-sync'; exit 1; }; \
	[[ -n "$${OPENAI_API_KEY:-}" ]] || { echo 'OPENAI_API_KEY is required for semantic-sync'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/semantic_sync.py --db-url "$(DATABASE_URL)" --limit "$${LIMIT:-100}" $${SEMANTIC_ARGS:-}

semantic-project: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-project'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/semantic_project.py --db-url "$(DATABASE_URL)" --projection-set "$${PROJECTION_SET:-pca_3d_latest}" --out-json "data/semantic/articles_points_$${PROJECTION_SET:-pca_3d_latest}.json" --out-html "data/semantic/semantic_map_$${PROJECTION_SET:-pca_3d_latest}.html" $${SEMANTIC_ARGS:-}

semantic-neighbors: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-neighbors'; exit 1; }; \
	[[ -n "$${ARTICLE_ID:-}" ]] || { echo 'ARTICLE_ID is required for semantic-neighbors'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/semantic_neighbors.py --db-url "$(DATABASE_URL)" --article-id "$${ARTICLE_ID}" --limit "$${LIMIT:-5}"

semantic-build: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-build'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/build_semantic_map.py --db-url "$(DATABASE_URL)" --limit "$${LIMIT:-500}" --projection-set "$${PROJECTION_SET:-pca_3d_latest}" $${SEMANTIC_ARGS:-}

semantic-smoke: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for semantic-smoke'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" $(PYTHON) scripts/build_semantic_map.py --db-url "$(DATABASE_URL)" --limit "$${LIMIT:-50}" --projection-set "$${PROJECTION_SET:-pca_3d_latest}" $${SEMANTIC_ARGS:-}

scheduler-dry-run:
	@DRY_RUN=1 DATABASE_URL="$(DATABASE_URL)" UV="$(UV)" bash "$(SCHEDULER_SCRIPT)"

scheduler-once:
	@DATABASE_URL="$(DATABASE_URL)" UV="$(UV)" bash "$(SCHEDULER_SCRIPT)"

stories-refresh-once:
	@DATABASE_URL="$(DATABASE_URL)" UV="$(UV)" bash scripts/run_stories_refresh.sh

explorer-refresh-once:
	@DATABASE_URL="$(DATABASE_URL)" OPENAI_API_KEY="$(OPENAI_API_KEY)" UV="$(UV)" bash scripts/run_explorer_refresh.sh

full-refresh-once:
	@$(MAKE) --no-print-directory stories-refresh-once DATABASE_URL="$(DATABASE_URL)" UV="$(UV)"
	@$(MAKE) --no-print-directory explorer-refresh-once DATABASE_URL="$(DATABASE_URL)" OPENAI_API_KEY="$(OPENAI_API_KEY)" UV="$(UV)"

status:
	@set -euo pipefail; \
	mkdir -p "$(STATE_DIR)"; \
	for file in last_status last_run_utc last_success_utc last_error consecutive_failures last_alert_utc; do \
	  if [[ -f "$(STATE_DIR)/$$file" ]]; then printf '%s=%s\n' "$$file" "$$(cat "$(STATE_DIR)/$$file")"; else printf '%s=%s\n' "$$file" '<missing>'; fi; \
	done

tail-log:
	@mkdir -p "$(LOG_DIR)"; tail -n 50 -f "$(LOG_DIR)/scheduler.log"

verify-output: preflight
	@set -euo pipefail; \
	missing=0; \
	if [[ -n "$(SOURCE)" ]]; then sources="$(SOURCE)"; else sources="$(SOURCES)"; fi; \
	for source in $$sources; do \
	  data_file="$(APP_ROOT)/data/$(OUT_PREFIX)_$${source}_$(DATE).json"; \
	  metrics_file="$(APP_ROOT)/logs/$(OUT_PREFIX)_$${source}_$(DATE)_metrics.json"; \
	  [[ -f "$$data_file" ]] || { echo "missing $$data_file"; missing=1; }; \
	  [[ -f "$$metrics_file" ]] || { echo "missing $$metrics_file"; missing=1; }; \
	done; \
	[[ $$missing -eq 0 ]] && echo 'output verification ok'

verify-db: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for verify-db'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(APP_ROOT):$${PYTHONPATH:-}" DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -c "import os; from sqlalchemy import text; from src.persistence.db import create_postgres_engine, resolve_db_url; engine=create_postgres_engine(resolve_db_url(os.environ['DATABASE_URL'])); conn=engine.connect(); print(f'articles_total={conn.execute(text(\"select count(*) from articles\")).scalar_one()}'); conn.close()"

db-url:
	@printf '%s\n' "$(LOCAL_DATABASE_URL)"

db-up:
	@set -euo pipefail; \
	command -v docker >/dev/null 2>&1 || { echo 'docker is required for db-up'; exit 1; }; \
	docker compose version >/dev/null 2>&1 || { echo 'docker compose is required for db-up'; exit 1; }; \
	[[ -f "$(COMPOSE_FILE)" ]] || { echo 'compose file missing: $(COMPOSE_FILE)'; exit 1; }; \
	$(DOCKER_COMPOSE) up -d $(LOCAL_DB_SERVICE); \
	echo 'local Postgres start requested'; \
	$(MAKE) --no-print-directory db-check

db-down:
	@set -euo pipefail; \
	command -v docker >/dev/null 2>&1 || { echo 'docker is required for db-down'; exit 1; }; \
	docker compose version >/dev/null 2>&1 || { echo 'docker compose is required for db-down'; exit 1; }; \
	[[ -f "$(COMPOSE_FILE)" ]] || { echo 'compose file missing: $(COMPOSE_FILE)'; exit 1; }; \
	$(DOCKER_COMPOSE) down

db-logs:
	@set -euo pipefail; \
	command -v docker >/dev/null 2>&1 || { echo 'docker is required for db-logs'; exit 1; }; \
	docker compose version >/dev/null 2>&1 || { echo 'docker compose is required for db-logs'; exit 1; }; \
	[[ -f "$(COMPOSE_FILE)" ]] || { echo 'compose file missing: $(COMPOSE_FILE)'; exit 1; }; \
	$(DOCKER_COMPOSE) logs -f $(LOCAL_DB_SERVICE)

db-psql:
	@set -euo pipefail; \
	command -v docker >/dev/null 2>&1 || { echo 'docker is required for db-psql'; exit 1; }; \
	docker compose version >/dev/null 2>&1 || { echo 'docker compose is required for db-psql'; exit 1; }; \
	[[ -f "$(COMPOSE_FILE)" ]] || { echo 'compose file missing: $(COMPOSE_FILE)'; exit 1; }; \
	$(DOCKER_COMPOSE) exec $(LOCAL_DB_SERVICE) psql -U "$(LOCAL_DB_USER)" -d "$(LOCAL_DB_NAME)"

db-check:
	@set -euo pipefail; \
	command -v docker >/dev/null 2>&1 || { echo 'docker is required for db-check'; exit 1; }; \
	docker compose version >/dev/null 2>&1 || { echo 'docker compose is required for db-check'; exit 1; }; \
	[[ -f "$(COMPOSE_FILE)" ]] || { echo 'compose file missing: $(COMPOSE_FILE)'; exit 1; }; \
	container_id="$$($(DOCKER_COMPOSE) ps -q $(LOCAL_DB_SERVICE))"; \
	[[ -n "$$container_id" ]] || { echo 'local Postgres container is not running; start it with make db-up'; exit 1; }; \
	docker exec "$$container_id" pg_isready -U "$(LOCAL_DB_USER)" -d "$(LOCAL_DB_NAME)" >/dev/null 2>&1 || { echo 'local Postgres is not ready yet'; exit 1; }; \
	echo "local Postgres ready at $(LOCAL_DB_HOST):$(LOCAL_DB_PORT) db=$(LOCAL_DB_NAME) user=$(LOCAL_DB_USER)"

clean-state:
	@mkdir -p "$(STATE_DIR)" "$(LOCK_DIR)"; \
	rm -f "$(STATE_DIR)/last_error"; \
	find "$(LOCK_DIR)" -maxdepth 1 -type f -name '*.lock' -print
