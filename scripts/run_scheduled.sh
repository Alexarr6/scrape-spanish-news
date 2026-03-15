#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UV="${UV:-${HOME}/.local/bin/uv}"
LOCAL_TZ="${LOCAL_TZ:-Europe/Madrid}"
SCHEDULER_RETRY_DELAY_SECONDS="${SCHEDULER_RETRY_DELAY_SECONDS:-120}"
SCHEDULER_MAX_RETRIES="${SCHEDULER_MAX_RETRIES:-1}"
ALERT_COOLDOWN_SECONDS="${ALERT_COOLDOWN_SECONDS:-43200}"
VAR_ROOT="$REPO_ROOT/var"
LOCK_DIR="$VAR_ROOT/lock"
LOG_DIR="$VAR_ROOT/log"
STATE_DIR="$VAR_ROOT/state"
LOCK_FILE="$LOCK_DIR/spain-news-bias-scraper.lock"
LOG_FILE="$LOG_DIR/scheduler.log"
DATE_LOCAL="$(TZ="$LOCAL_TZ" date +%F)"
DATE_UTC_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DRY_RUN="${DRY_RUN:-0}"
ALERT_COMMAND="${ALERT_COMMAND:-}"
CONSECUTIVE_FAILURES_FILE="$STATE_DIR/consecutive_failures"
LAST_ALERT_FILE="$STATE_DIR/last_alert_utc"
LAST_ERROR_FILE="$STATE_DIR/last_error"
LAST_STATUS_FILE="$STATE_DIR/last_status"
LAST_RUN_FILE="$STATE_DIR/last_run_utc"
LAST_SUCCESS_FILE="$STATE_DIR/last_success_utc"

mkdir -p "$LOCK_DIR" "$LOG_DIR" "$STATE_DIR"
exec >>"$LOG_FILE" 2>&1

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

write_state() {
  printf '%s\n' "$2" >"$1"
}

read_int_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    tr -dc '0-9' <"$file"
  else
    printf '0'
  fi
}

maybe_alert() {
  local message="$1"
  local failures
  failures="$(read_int_file "$CONSECUTIVE_FAILURES_FILE")"
  [[ -n "$ALERT_COMMAND" ]] || return 0
  [[ "$failures" -ge 2 ]] || return 0

  local now_epoch last_epoch=0
  now_epoch="$(date -u +%s)"
  if [[ -f "$LAST_ALERT_FILE" ]]; then
    last_epoch="$(date -u -d "$(cat "$LAST_ALERT_FILE")" +%s 2>/dev/null || echo 0)"
  fi
  if (( now_epoch - last_epoch < ALERT_COOLDOWN_SECONDS )); then
    log "alert cooldown active; skipping alert"
    return 0
  fi

  log "running alert hook"
  if "$ALERT_COMMAND" "$message"; then
    write_state "$LAST_ALERT_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  else
    log "alert hook failed"
  fi
}

run_attempt() {
  local attempt="$1"
  log "attempt ${attempt}: preflight"
  make --no-print-directory -C "$REPO_ROOT" preflight UV="$UV"
  log "attempt ${attempt}: run-all-persist date=$DATE_LOCAL"
  make --no-print-directory -C "$REPO_ROOT" run-all-persist DATE="$DATE_LOCAL" OUT_PREFIX=sched DATABASE_URL="$DATABASE_URL" UV="$UV"
  log "attempt ${attempt}: verify-output date=$DATE_LOCAL"
  make --no-print-directory -C "$REPO_ROOT" verify-output DATE="$DATE_LOCAL" OUT_PREFIX=sched UV="$UV"
  if [[ -n "${DATABASE_URL:-}" ]]; then
    log "attempt ${attempt}: verify-db"
    make --no-print-directory -C "$REPO_ROOT" verify-db DATABASE_URL="$DATABASE_URL" UV="$UV"
  fi
}

if [[ "$DRY_RUN" == "1" ]]; then
  log "dry-run app_root=$REPO_ROOT date=$DATE_LOCAL max_retries=$SCHEDULER_MAX_RETRIES uv=$UV"
  log "dry-run command: make -C $REPO_ROOT run-all-persist DATE=$DATE_LOCAL OUT_PREFIX=sched UV=$UV"
  exit 0
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  log "fatal: DATABASE_URL is required for scheduled persistent runs"
  write_state "$LAST_STATUS_FILE" "preflight_failed"
  write_state "$LAST_RUN_FILE" "$DATE_UTC_NOW"
  write_state "$LAST_ERROR_FILE" "DATABASE_URL missing"
  exit 1
fi

if ! command -v "$UV" >/dev/null 2>&1; then
  log "fatal: uv is required for scheduled runs"
  write_state "$LAST_STATUS_FILE" "preflight_failed"
  write_state "$LAST_RUN_FILE" "$DATE_UTC_NOW"
  write_state "$LAST_ERROR_FILE" "uv missing"
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "skip: previous run still active"
  write_state "$LAST_STATUS_FILE" "lock_busy"
  write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exit 0
fi

log "scheduler start app_root=$REPO_ROOT date=$DATE_LOCAL uv=$UV"

attempt=0
max_attempts=$((SCHEDULER_MAX_RETRIES + 1))
while (( attempt < max_attempts )); do
  attempt=$((attempt + 1))
  if run_attempt "$attempt"; then
    log "scheduler success on attempt $attempt"
    write_state "$LAST_STATUS_FILE" "ok"
    write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_state "$LAST_SUCCESS_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_state "$LAST_ERROR_FILE" ""
    write_state "$CONSECUTIVE_FAILURES_FILE" "0"
    exit 0
  else
    rc=$?
    log "attempt $attempt failed rc=$rc"
  fi

  if (( attempt < max_attempts )); then
    log "sleeping ${SCHEDULER_RETRY_DELAY_SECONDS}s before retry"
    sleep "$SCHEDULER_RETRY_DELAY_SECONDS"
  fi
done

failures=$(( $(read_int_file "$CONSECUTIVE_FAILURES_FILE") + 1 ))
write_state "$CONSECUTIVE_FAILURES_FILE" "$failures"
write_state "$LAST_STATUS_FILE" "failed"
write_state "$LAST_RUN_FILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "$LAST_ERROR_FILE" "scheduled run failed after ${max_attempts} attempt(s) for date $DATE_LOCAL"
log "scheduler failed after ${max_attempts} attempt(s); consecutive_failures=$failures"
maybe_alert "spain-news-bias-scraper scheduled run failed (${failures} consecutive failures)"
exit 1
