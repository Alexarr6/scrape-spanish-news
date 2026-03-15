- State: HYGIENE_PASS_1_DONE
- Current phase: hygiene guardrails landed; repo is root-first, checks are enforced locally, and contract tests no longer depend on archived run paths
- Last update: 2026-03-15 18:26 UTC

## Hygiene pass outcome
- Added `.pre-commit-config.yaml` with only `ruff-check` and `ruff-format`, and added `pre-commit` to the dev dependency group.
- Added `make pre-commit` and canonical `make check` (`pre-commit` + tests) aligned with the root-first `uv` workflow.
- Removed dead legacy script `scripts/detect_app_root.sh` and updated docs to stop mentioning it.
- Promoted the active archived evidence used by contract tests into `tests/fixtures/evidence/20260314-1212-8ff9/`.
- Pruned obvious noise: repo/test caches, tracked archived `.pyc` files, and stale archived run virtualenv directories.

## Remaining highest-priority work
1. Refactor `src/persistence/crud.py` batch ingest semantics so transaction behavior is explicit and tested.
2. Add DB-backed tests for insert/update/failure behavior around ingest.
3. Add FastAPI route tests for 200/404/422 and dependency/session override paths.
4. Continue pruning archived run sludge that is no longer needed for evidence or audit history.

## Verification target for this phase
```bash
uv run pre-commit run --all-files
make check
make test
make scheduler-dry-run
```
