SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

APP_ROOT ?= $(shell bash scripts/detect_app_root.sh)
PYTHON ?= python3
LOCAL_TZ ?= Europe/Madrid
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
LEGACY_SITE_PACKAGES := $(firstword $(wildcard $(APP_ROOT)/.venv/lib/python*/site-packages))
PYTHONPATH_VALUE := $(APP_ROOT)$(if $(LEGACY_SITE_PACKAGES),:$(LEGACY_SITE_PACKAGES))
COMPOSE_FILE ?= compose.yaml
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE)
LOCAL_DB_SERVICE ?= postgres
LOCAL_DB_HOST ?= 127.0.0.1
LOCAL_DB_PORT ?= 5432
LOCAL_DB_NAME ?= spain_news_bias
LOCAL_DB_USER ?= spain_news
LOCAL_DB_PASSWORD ?= spain_news_dev
LOCAL_DATABASE_URL := postgresql://$(LOCAL_DB_USER):$(LOCAL_DB_PASSWORD)@$(LOCAL_DB_HOST):$(LOCAL_DB_PORT)/$(LOCAL_DB_NAME)

.PHONY: help print-app-root preflight test smoke run-source run-source-persist run-all run-all-persist api scheduler-once scheduler-dry-run status tail-log verify-output verify-db db-url db-up db-down db-logs db-psql db-check clean-state

help:
	@printf '%s\n' \
	  'Root operator surface for spain-news-bias-scraper' \
	  '' \
	  'Targets:' \
	  '  make preflight                Check runtime, lock tool, and detected app root' \
	  '  make test                     Run tests from detected app root' \
	  '  make smoke SOURCE=elpais      Quick non-persistent scrape' \
	  '  make run-source SOURCE=...    Run one source for DATE=$(DATE)' \
	  '  make run-source-persist SOURCE=... DATABASE_URL=postgresql://...' \
	  '  make run-all                  Run all sources sequentially without persistence' \
	  '  make run-all-persist          Run all sources sequentially with persistence' \
	  '  make api DATABASE_URL=...     Run FastAPI app via uvicorn' \
	  '  make scheduler-dry-run        Show scheduled execution plan' \
	  '  make scheduler-once           Run the scheduler wrapper once' \
	  '  make status                   Show scheduler state files' \
	  '  make tail-log                 Tail scheduler log' \
	  '  make verify-output            Check expected JSON/metrics files for DATE' \
	  '  make verify-db DATABASE_URL=postgresql://...  Check article row count' \
	  '  make db-url                   Print the local dev DATABASE_URL' \
	  '  make db-up                    Start optional local Postgres via Docker Compose' \
	  '  make db-down                  Stop optional local Postgres' \
	  '  make db-logs                  Tail local Postgres logs' \
	  '  make db-psql                  Open psql inside the local Postgres container' \
	  '  make db-check                 Wait for local Postgres readiness' \
	  '' \
	  'Notes:' \
	  '  - Repo root is the operator surface.' \
	  '  - The runnable app root is auto-detected; override with APP_ROOT=... if needed.' \
	  '  - Docker is optional; host-based non-persistent runs do not need it.'

print-app-root:
	@printf '%s\n' "$(APP_ROOT)"

preflight:
	@set -euo pipefail; \
	mkdir -p "$(LOCK_DIR)" "$(LOG_DIR)" "$(STATE_DIR)"; \
	printf 'repo_root=%s\n' "$$PWD"; \
	printf 'app_root=%s\n' "$(APP_ROOT)"; \
	command -v "$(PYTHON)" >/dev/null || { echo 'python missing'; exit 1; }; \
	command -v flock >/dev/null || { echo 'flock missing'; exit 1; }; \
	[[ -d "$(APP_ROOT)" ]] || { echo 'app root missing'; exit 1; }; \
	[[ -f "$(APP_ROOT)/src/main.py" ]] || { echo 'src/main.py missing under app root'; exit 1; }; \
	if [[ -n "$(LEGACY_SITE_PACKAGES)" ]]; then printf 'legacy_site_packages=%s\n' "$(LEGACY_SITE_PACKAGES)"; else echo 'warning: no embedded site-packages detected; relying on host python environment'; fi; \
	if [[ -z "$(DATABASE_URL)" ]]; then echo 'warning: DATABASE_URL not set; persist/api targets will fail until you provide it'; fi; \
	if ! command -v docker >/dev/null 2>&1; then echo 'warning: docker not found; host-based mode is the intended default'; fi; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$(PYTHON)" -m src.main --help >/dev/null; \
	echo 'python entrypoint ok'


test: preflight
	@cd "$(APP_ROOT)" && \
	if PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$(PYTHON)" -c "import pytest" >/dev/null 2>&1; then \
	  PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$(PYTHON)" -m pytest -q tests; \
	else \
	  echo 'pytest not available; falling back to unittest discovery'; \
	  PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$(PYTHON)" -m unittest discover -s tests -p 'test_*.py'; \
	fi

smoke: preflight
	@$(MAKE) --no-print-directory run-source SOURCE="$(if $(SOURCE),$(SOURCE),elpais)" DATE="$(DATE)" OUT_PREFIX=smoke MAX_DISCOVERY_URLS=20 MAX_ARTICLES_TO_EXTRACT=10 MAX_RUNTIME_SECONDS=45

run-source: preflight
	@set -euo pipefail; \
	[[ -n "$(SOURCE)" ]] || { echo 'SOURCE is required'; exit 1; }; \
	mkdir -p "$(APP_ROOT)/data" "$(APP_ROOT)/logs"; \
	cmd=("$(PYTHON)" -m src.main --source "$(SOURCE)" --date "$(DATE)" --out "data/$(OUT_PREFIX)_$(SOURCE)_$(DATE).json" --metrics-out "logs/$(OUT_PREFIX)_$(SOURCE)_$(DATE)_metrics.json" --max-discovery-urls "$${MAX_DISCOVERY_URLS:-300}" --max-articles-to-extract "$${MAX_ARTICLES_TO_EXTRACT:-120}" --max-runtime-seconds "$${MAX_RUNTIME_SECONDS:-180}"); \
	if [[ "$${PERSIST:-0}" == 1 ]]; then \
	  [[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for persistence'; exit 1; }; \
	  cmd+=(--persist --db-url "$(DATABASE_URL)"); \
	fi; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$${cmd[@]}"

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
	@cd "$(APP_ROOT)" && PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" "$(PYTHON)" -m uvicorn src.api.app:create_app --factory --host "$(API_HOST)" --port "$(API_PORT)"

scheduler-dry-run:
	@DRY_RUN=1 APP_ROOT="$(APP_ROOT)" DATABASE_URL="$(DATABASE_URL)" bash "$(SCHEDULER_SCRIPT)"

scheduler-once:
	@APP_ROOT="$(APP_ROOT)" DATABASE_URL="$(DATABASE_URL)" bash "$(SCHEDULER_SCRIPT)"

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
	for source in $(SOURCES); do \
	  data_file="$(APP_ROOT)/data/$(OUT_PREFIX)_$$source_$(DATE).json"; \
	  metrics_file="$(APP_ROOT)/logs/$(OUT_PREFIX)_$$source_$(DATE)_metrics.json"; \
	  [[ -f "$$data_file" ]] || { echo "missing $$data_file"; missing=1; }; \
	  [[ -f "$$metrics_file" ]] || { echo "missing $$metrics_file"; missing=1; }; \
	done; \
	[[ $$missing -eq 0 ]] && echo 'output verification ok'

verify-db: preflight
	@set -euo pipefail; \
	[[ -n "$(DATABASE_URL)" ]] || { echo 'DATABASE_URL is required for verify-db'; exit 1; }; \
	cd "$(APP_ROOT)" && PYTHONPATH="$(PYTHONPATH_VALUE):$${PYTHONPATH:-}" DATABASE_URL="$(DATABASE_URL)" "$(PYTHON)" -c "import os; from sqlalchemy import text; from src.persistence.db import create_postgres_engine, resolve_db_url; engine=create_postgres_engine(resolve_db_url(os.environ['DATABASE_URL'])); conn=engine.connect(); print(f'articles_total={conn.execute(text(\"select count(*) from articles\")).scalar_one()}'); conn.close()"

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
