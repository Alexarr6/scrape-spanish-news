#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "${APP_ROOT:-}" ]]; then
  if [[ -f "$REPO_ROOT/$APP_ROOT/src/main.py" ]]; then
    printf '%s\n' "$APP_ROOT"
    exit 0
  fi
  printf 'APP_ROOT override does not look runnable: %s\n' "$APP_ROOT" >&2
  exit 1
fi

if [[ -f "$REPO_ROOT/src/main.py" ]]; then
  printf '.\n'
  exit 0
fi

best=""
while IFS= read -r candidate; do
  rel="${candidate#"$REPO_ROOT"/}"
  if [[ -z "$best" || "$rel" > "$best" ]]; then
    best="$rel"
  fi
done < <(find "$REPO_ROOT/runs" -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/src/main.py' ';' -print 2>/dev/null | sort)

if [[ -n "$best" ]]; then
  printf '%s\n' "$best"
  exit 0
fi

printf 'No runnable app root found under repo root or runs/\n' >&2
exit 1
