#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UV="${UV:-${HOME}/.local/bin/uv}"
DAYS_BACK="${DAYS_BACK:-3}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-large}"
PROJECTION_SET="${PROJECTION_SET:-pca_3d_latest}"
SEMANTIC_LIMIT="${SEMANTIC_LIMIT:-100}"
SEMANTIC_BUILD_LIMIT="${SEMANTIC_BUILD_LIMIT:-500}"
VAR_ROOT="$REPO_ROOT/var"
LOCK_DIR="$VAR_ROOT/lock"
LOG_DIR="$VAR_ROOT/log"
STATE_DIR="$VAR_ROOT/state"
LOCK_FILE="$LOCK_DIR/explorer-refresh.lock"
LOG_FILE="$LOG_DIR/explorer-refresh.log"
LAST_STATUS_FILE="$STATE_DIR/explorer_last_status"
LAST_RUN_FILE="$STATE_DIR/explorer_last_run_utc"
LAST_SUCCESS_FILE="$STATE_DIR/explorer_last_success_utc"
LAST_ERROR_FILE="$STATE_DIR/explorer_last_error"
START_EPOCH="$(date -u +%s)"

mkdir -p "$LOCK_DIR" "$LOG_DIR" "$STATE_DIR"
exec >>"$LOG_FILE" 2>&1

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

write_state() {
  printf '%s\n' "$2" >"$1"
}

require_env() {
  local name="$1"
  [[ -n "${!name:-}" ]] || {
    log "fatal: ${name} is required"
    write_state "$LAST_STATUS_FILE" "preflight_failed"
    write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_state "$LAST_ERROR_FILE" "${name} missing"
    exit 1
  }
}

run_step() {
  local step="$1"
  shift
  log "step: ${step}"
  "$@"
}

require_env DATABASE_URL
require_env OPENAI_API_KEY

if ! command -v "$UV" >/dev/null 2>&1; then
  log "fatal: uv is required for explorer refresh"
  write_state "$LAST_STATUS_FILE" "preflight_failed"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  write_state "$LAST_ERROR_FILE" "uv missing"
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "skip: previous explorer refresh still active"
  write_state "$LAST_STATUS_FILE" "lock_busy"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exit 0
fi

finish_failure() {
  local rc="$1"
  local elapsed=$(( $(date -u +%s) - START_EPOCH ))
  write_state "$LAST_STATUS_FILE" "failed"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  write_state "$LAST_ERROR_FILE" "explorer refresh failed rc=${rc} model=${EMBEDDING_MODEL}"
  log "explorer refresh failed rc=${rc} elapsed_seconds=${elapsed}"
  exit "$rc"
}
trap 'finish_failure "$?"' ERR

log "explorer refresh start repo_root=$REPO_ROOT days_back=$DAYS_BACK embedding_model=$EMBEDDING_MODEL projection_set=$PROJECTION_SET semantic_limit=$SEMANTIC_LIMIT semantic_build_limit=$SEMANTIC_BUILD_LIMIT uv=$UV"

run_step preflight \
  make --no-print-directory -C "$REPO_ROOT" preflight UV="$UV"

run_step semantic-db-init \
  make --no-print-directory -C "$REPO_ROOT" semantic-db-init \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    SEMANTIC_ARGS="--embedding-model $EMBEDDING_MODEL"

run_step semantic-sync \
  make --no-print-directory -C "$REPO_ROOT" semantic-sync \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    LIMIT="$SEMANTIC_LIMIT" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    SEMANTIC_ARGS="--embedding-model $EMBEDDING_MODEL --days-back $DAYS_BACK --prioritize-story-members"

run_step semantic-project \
  make --no-print-directory -C "$REPO_ROOT" semantic-project \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    PROJECTION_SET="$PROJECTION_SET" \
    SEMANTIC_ARGS="--days-back $DAYS_BACK"

run_step semantic-build \
  make --no-print-directory -C "$REPO_ROOT" semantic-build \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    LIMIT="$SEMANTIC_BUILD_LIMIT" \
    PROJECTION_SET="$PROJECTION_SET" \
    SEMANTIC_ARGS="--days-back $DAYS_BACK"

trap - ERR
elapsed=$(( $(date -u +%s) - START_EPOCH ))
write_state "$LAST_STATUS_FILE" "ok"
write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "$LAST_SUCCESS_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "$LAST_ERROR_FILE" ""
log "explorer refresh success elapsed_seconds=${elapsed}"
