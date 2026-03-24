- State: DONE
- Current phase: iter/008 frontend UX correction landed for the article-type lens control; repo ready for final review
- Last update: 2026-03-24 UTC

## iter/008 bounded slice summary
- backend/data slice landed lightweight `editorial_preview`, article-type query support, and bounded editorial meta/counts for Explorer
- frontend slice now wires that contract into Explorer URL/query state, map matching logic, legend copy, and control-bar UX
- added the first bounded `Editorial lens` control for **Article type** only
- added `sem_color=article-type` categorical coloring for visible points
- preserved approved mode semantics:
  - `sem_mode=highlight` keeps the full cloud visible and emphasizes matching article types
  - `sem_mode=filter` shows the backend-narrowed article-type subset clearly as a narrowed view
- added legend/context handling for `unknown`, `pending`, `failed`, `limited`, and `out_of_domain`
- kept the slice deliberately narrow: no bias/tone lensing, no multi-dimension builder, no Phase 1 visual grammar churn
- bounded cleanup pass tightened the point-level `editorial_preview` contract to the fields Explorer actually promises today
- legend/dataset copy now says coverage more honestly instead of implying all visible points are analyzed
- article-type color semantics now better match the explanatory copy:
  - pending / failed / unknown / out-of-domain render with diagnostic-muted colors
  - limited keeps its article-type hue but is visually muted instead of pretending to be a separate type

## verification status
- passed: `python3 -m py_compile src/api/contracts/semantic.py src/api/v1/semantic.py src/semantic/contracts.py src/semantic/dbstore.py tests/test_api_semantic_explorer.py`
- passed: `/home/node/.local/bin/uv run --group dev python -m pytest tests/test_api_semantic_explorer.py`
- passed: `cd frontend && npm run build`
- passed: `cd frontend && npm run build` after the bounded article-type lens toolbar UX correction

## frontend UX correction follow-up
- replaced the stacked `Editorial lens` label + select + separate clear button with a compact inline toolbar trigger that sits cleanly beside the surrounding segmented controls
- trigger now reads `Article type` by default and `Type: <Value>` when active
- clear/reset moved inside the opened menu as a first menu action instead of living as a separate always-visible button
- removed the redundant right-side `Article type lens` badge noise while preserving the current article-type URL/query behavior
- tightened control styling so the article-type lens matches the toolbar’s height, baseline rhythm, and active-state treatment

## files changed in this pass
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/contracts.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/query.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/explorerEditorial.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/styles.css`
- `STATUS.md`
- `RESULTS.md`

- State: DONE
- Current phase: iter/007 final bounded implementer follow-up landed; repo ready for review
- Last update: 2026-03-23 UTC

## iter/007 bounded follow-up summary
- landed source-aware semantic selection in two downstream places that were still amplifying source skew via global recent-row caps:
  - `select_embedding_candidates()` now round-robins stale/missing embedding work across sources after recency filtering instead of taking the first globally recent rows
  - `build_semantic_map.py` now uses source-balanced article-id selection for the exported bounded slice instead of a raw first-N recency cut
- refined `elDiario` layered-discovery skip behavior so sitemap/html fallback layers can skip based on likely usable/fresh candidates rather than raw accepted URL volume alone
- surfaced cluster membership diagnostics in Stories article detail so users can inspect why a member article belongs in a cluster without spelunking backend JSON
- kept the pass bounded: no clustering rewrite, no new explorer contract churn, no changes to the already-fixed Stories → Explorer handoff logic

## review-relevant notes
- the highest-leverage issue from the architect review was downstream source-skew amplification from global caps; this pass addresses that in the semantic sync/build slice without inventing a giant re-ranking framework
- `elDiario` freshness/usable heuristics remain deliberately modest:
  - same-day URLs count as clearly usable
  - explicitly dated stale URLs no longer satisfy the skip threshold
  - undated but section-valid URLs can still count, which avoids dropping plausible article pages too aggressively
- Stories now exposes `membership_diagnostics` in the article-detail panel with:
  - support edge count
  - best / mean support score
  - guarded-merge marker
  - risky-bridge marker
  - penalties
  - quick links to supporting article ids

## verification status
- passed: `python3 -m unittest tests.test_eldiario_adapter`
- passed: `python3 -m py_compile src/semantic/dbstore.py src/adapters/eldiario.py src/adapters/layered_discovery.py scripts/build_semantic_map.py`
- passed: `cd frontend && npm run build`
- blocked environment:
  - repo `.venv/bin/python` points at a dead interpreter path, so the targeted pytest slice could not be run from the repo venv in this container
  - system Python in this container also lacks project deps like `sqlalchemy`, so deeper backend runtime smoke tests were constrained

## files changed in this pass
- `src/semantic/dbstore.py`
- `scripts/build_semantic_map.py`
- `src/adapters/layered_discovery.py`
- `src/adapters/eldiario.py`
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/lib/types.ts`
- `tests/test_eldiario_adapter.py`
- `tests/test_semantic_dbstore.py`
- `STATUS.md`
- `RESULTS.md`

## remaining bounded follow-up ideas
- if review still sees source skew, the next move should be extending source-aware capping to other globally bounded downstream stages (`ENRICH_LIMIT`, cluster build windows), not undoing this pass
- if Stories needs more debuggability later, a small next step would be showing membership diagnostics inline in source-group cards, not just article detail
