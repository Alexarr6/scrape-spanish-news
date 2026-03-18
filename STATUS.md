- State: TEMPORAL_WINDOW_PHASE_DONE
- Current phase: bounded semantic DB windowing + analysis memory optimization
- Last update: 2026-03-18 14:55 UTC
- Pending approvals: none

## Completed in this iteration
- Replaced the ambiguous follow-up with the bounded temporal-window phase from `PLAN.md`.
- Added a reusable semantic window contract in `src/semantic/dbstore.py` via `resolve_semantic_window()` and `SemanticWindow`.
- Wired `--days-back`, `--date-from`, and `--date-to` through:
  - `scripts/semantic_sync.py`
  - `scripts/semantic_project.py`
  - `scripts/build_semantic_map.py`
- Applied the window contract to:
  - semantic sync candidate selection
  - embedding artifact loading
  - projection-set rebuilds
  - projected-point loads used by the build/export path
- Kept no-window behavior backward-compatible: full history still runs when no window flags are passed.
- Replaced the worst analysis-time O(N^2) memory spike in `src/semantic/analyze.py`:
  - clustering still runs on normalized embeddings
  - local density and nearby-source signals now come from nearest-neighbor queries instead of a full pairwise distance matrix
- Added regression coverage for temporal window normalization / SQL plumbing and the nearest-neighbor analysis path.

## Verification run
- `~/.local/bin/uv run pytest -q tests/test_semantic_analysis.py tests/test_semantic_dbstore.py tests/test_semantic_build_cli.py tests/test_api_semantic_explorer.py`
  - Result: `33 passed`

## Atomic commits created
- `047b42f` — `Add temporal window support to semantic sync and projection dbstore flow`
- `e78f781` — `Reduce semantic analysis memory pressure and add regression coverage`

## Remaining caveats
- No live Postgres smoke was executed in this session because no concrete `DATABASE_URL` for an honest Raspberry/remote run was provided here.
- In bounded mode, `refresh_projection_set()` clears and rebuilds the named `projection_set` for the bounded slice so the set stays internally consistent instead of mixing old global rows with fresh windowed rows.
