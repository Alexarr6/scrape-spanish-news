#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UV="${UV:-${HOME}/.local/bin/uv}"
LOCAL_TZ="${LOCAL_TZ:-Europe/Madrid}"
DAYS_BACK="${DAYS_BACK:-${REFRESH_DAYS_BACK:-3}}"
CLUSTER_LIMIT="${CLUSTER_LIMIT:-${SURFACE_LIMIT:-500}}"
ENRICH_LIMIT="${ENRICH_LIMIT:-$(( CLUSTER_LIMIT * 2 > ${SURFACE_LIMIT:-500} ? CLUSTER_LIMIT * 2 : ${SURFACE_LIMIT:-500} ))}"
SCORE_THRESHOLD="${SCORE_THRESHOLD:-0.45}"
OUT_PREFIX="${OUT_PREFIX:-sched}"
VAR_ROOT="$REPO_ROOT/var"
LOCK_DIR="$VAR_ROOT/lock"
LOG_DIR="$VAR_ROOT/log"
STATE_DIR="$VAR_ROOT/state"
LOCK_FILE="$LOCK_DIR/stories-refresh.lock"
LOG_FILE="$LOG_DIR/stories-refresh.log"
LAST_STATUS_FILE="$STATE_DIR/stories_last_status"
LAST_RUN_FILE="$STATE_DIR/stories_last_run_utc"
LAST_SUCCESS_FILE="$STATE_DIR/stories_last_success_utc"
LAST_ERROR_FILE="$STATE_DIR/stories_last_error"
DATE_LOCAL="$(TZ="$LOCAL_TZ" date +%F)"
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

if ! command -v "$UV" >/dev/null 2>&1; then
  log "fatal: uv is required for stories refresh"
  write_state "$LAST_STATUS_FILE" "preflight_failed"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  write_state "$LAST_ERROR_FILE" "uv missing"
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "skip: previous stories refresh still active"
  write_state "$LAST_STATUS_FILE" "lock_busy"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exit 0
fi

finish_failure() {
  local rc="$1"
  local elapsed=$(( $(date -u +%s) - START_EPOCH ))
  write_state "$LAST_STATUS_FILE" "failed"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  write_state "$LAST_ERROR_FILE" "stories refresh failed rc=${rc} date=${DATE_LOCAL}"
  log "stories refresh failed rc=${rc} elapsed_seconds=${elapsed}"
  exit "$rc"
}
trap 'finish_failure "$?"' ERR

log "stories refresh start repo_root=$REPO_ROOT date_local=$DATE_LOCAL days_back=$DAYS_BACK enrich_limit=$ENRICH_LIMIT cluster_limit=$CLUSTER_LIMIT score_threshold=$SCORE_THRESHOLD out_prefix=$OUT_PREFIX uv=$UV"

run_step preflight \
  make --no-print-directory -C "$REPO_ROOT" preflight UV="$UV"

run_step run-all-persist \
  make --no-print-directory -C "$REPO_ROOT" run-all-persist \
    DATE="$DATE_LOCAL" \
    OUT_PREFIX="$OUT_PREFIX" \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV"

run_step analysis-db-init \
  make --no-print-directory -C "$REPO_ROOT" analysis-db-init \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV"

run_step enrich-articles \
  make --no-print-directory -C "$REPO_ROOT" enrich-articles \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    DAYS_BACK="$DAYS_BACK" \
    LIMIT="$ENRICH_LIMIT"

run_step build-story-clusters \
  make --no-print-directory -C "$REPO_ROOT" build-story-clusters \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV" \
    DAYS_BACK="$DAYS_BACK" \
    LIMIT="$CLUSTER_LIMIT" \
    SCORE_THRESHOLD="$SCORE_THRESHOLD"

run_step verify-output \
  make --no-print-directory -C "$REPO_ROOT" verify-output \
    DATE="$DATE_LOCAL" \
    OUT_PREFIX="$OUT_PREFIX" \
    UV="$UV"

run_step verify-db \
  make --no-print-directory -C "$REPO_ROOT" verify-db \
    DATABASE_URL="$DATABASE_URL" \
    UV="$UV"

trap - ERR
elapsed=$(( $(date -u +%s) - START_EPOCH ))
write_state "$LAST_STATUS_FILE" "ok"
write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "$LAST_SUCCESS_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "$LAST_ERROR_FILE" ""
log "stories refresh success elapsed_seconds=${elapsed}"
