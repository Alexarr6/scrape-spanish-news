## 2026-03-23 — bounded final implementer follow-up for iter/007

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** bounded architect-review follow-up focused on downstream source skew, `elDiario` usable-candidate skip thresholds, and Stories cluster-membership diagnostics

### What I accomplished
- fixed the highest-leverage downstream skew amplifier in semantic sync:
  - `src/semantic/dbstore.py::select_embedding_candidates()` still over-fetched by recency and then took the first stale/missing rows globally
  - changed it to keep the recency gate but select the bounded batch round-robin across sources after stale/missing filtering
- fixed the same downstream skew pattern in semantic export/build slicing:
  - added `select_source_balanced_article_ids()` in `src/semantic/dbstore.py`
  - switched `scripts/build_semantic_map.py` to use that helper instead of a raw first-`N` recency slice when choosing the bounded point/export payload
- refined `elDiario` layered discovery so fallback-layer skipping depends on likely usable candidates rather than raw URL count:
  - extended `DiscoveryLayer` with an optional `should_skip` predicate in `src/adapters/layered_discovery.py`
  - updated `src/adapters/eldiario.py` so sitemap/html fallback skip decisions are based on a small freshness-aware usability heuristic
  - explicitly dated stale URLs no longer let early layers falsely suppress fallback discovery
- exposed cluster membership diagnostics in Stories article detail:
  - added `membership_diagnostics` typing in `frontend/src/lib/types.ts`
  - added a sober `Cluster membership` section in `frontend/src/components/stories/StoryFocusPanel.tsx`
  - surface includes support-edge counts, best/mean support, guarded-merge marker, risky-bridge marker, penalties, and quick links to supporting member articles

### Why this is the right bounded fix
- the architect’s main complaint was real: recent-row global caps were still letting one source dominate the semantic bounded slice
- this pass fixes that where it was easiest to do responsibly without dragging the repo into a giant ranking-framework rewrite
- the `elDiario` tweak is intentionally conservative: enough to stop raw stale-volume skip mistakes, not aggressive enough to start nuking plausible undated article pages
- the Stories UI diagnostic section uses already-persisted `membership_diagnostics`; no new backend payload invention was needed

### Files changed
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

### Verification
Commands run:
- `python3 -m unittest tests.test_eldiario_adapter`
- `python3 -m py_compile src/semantic/dbstore.py src/adapters/eldiario.py src/adapters/layered_discovery.py scripts/build_semantic_map.py`
- `cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper/frontend && npm run build`

Results:
- `unittest` slice for `elDiario`: passed (`3 tests`)
- backend syntax compile for touched Python files: passed
- frontend production build/typecheck: passed
- repo pytest slice: **could not run in this container** because `.venv/bin/python` points at a dead interpreter path, and the system Python lacks project deps like `sqlalchemy`

### Relevant details for review
- there were already unrelated dirty files in the repo worktree when I started (`ARCH_REVIEW.md`, some existing frontend files already modified); I kept this pass bounded to the follow-up scope instead of trying to clean unrelated state
- no commit was created in this pass

### What remains
- broad project pytest verification still needs a healthy Python env / working repo venv
- if another bounded iteration happens, the next best target is extending source-aware caps to other downstream bounded stages outside semantic sync/build, not revisiting this same slice again
