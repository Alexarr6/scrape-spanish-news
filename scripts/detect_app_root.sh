#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/src/main.py" ]]; then
  printf 'Root app is not runnable: missing %s\n' "$REPO_ROOT/src/main.py" >&2
  exit 1
fi

printf '.\n'
