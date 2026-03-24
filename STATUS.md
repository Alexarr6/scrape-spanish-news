- State: DONE
- Current phase: iter/008 explorer article-type editorial lens backend landed; ready for frontend integration/review
- Last update: 2026-03-24 UTC

## iter/008 bounded backend slice summary
- added lightweight `editorial_preview` onto Explorer point payloads so the point cloud can read article-type/editorial state without dragging full article-detail editorial blobs
- added `/api/v1/semantic/explorer/points` editorial lens query support for:
  - `sem_editorial_dim=article_type`
  - `sem_editorial_value=<label>`
- preserved mode semantics:
  - `sem_mode=filter` narrows the explorer dataset to matching article type
  - `sem_mode=highlight` keeps the broader dataset and still returns preview payloads for all visible points
- landed bounded Explorer editorial meta/filter support for article-type options plus simple coverage counts
- kept the pass deliberately narrow: no bias/tone lensing, no endpoint architecture rewrite, no Phase 1 visual grammar churn

## verification status
- passed: `python3 -m py_compile src/api/contracts/semantic.py src/api/v1/semantic.py src/semantic/contracts.py src/semantic/dbstore.py tests/test_api_semantic_explorer.py`
- passed: `/home/node/.local/bin/uv run --group dev python -m pytest tests/test_api_semantic_explorer.py`

## files changed in this pass
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/contracts.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- `frontend/src/lib/types.ts`
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
