- State: DONE
- Current phase: iter/007 Phase C implementer freshness-first discovery hardening completed; repo ready for final whole-project architect review
- Last update: 2026-03-23 UTC

## iter/007 Phase C architect status
- replaced `ARCH_REVIEW.md` with a deep repo-specific scrape coverage review covering adapters, runtime windows, discovery attrition, downstream skew amplification, and per-source diagnosis
- reviewed current scrape/runtime code across:
  - `src/core/adapter.py`
  - `src/adapters/{elpais,elmundo,abc,lavanguardia,eldiario,minutos20}.py`
  - `src/adapters/{layered_discovery,rss_adapter,url_filters}.py`
  - `scripts/{run_scheduled,run_stories_refresh,run_explorer_refresh}.sh`
  - relevant enrichment / clustering / semantic windowing code
- used repo evidence from current metrics/data artifacts rather than vibes, including scheduled metrics from 2026-03-15..23 and semantic export counts from `data/semantic/articles_points_20260323-113527.json`

## Architect conclusions
- source imbalance is a mix of real publisher volume differences and self-inflicted pipeline bias
- El País high counts are mostly real and aided by a clean RSS-heavy funnel
- 20minutos and El Mundo look comparatively honest, just smaller/narrower
- elDiario appears underrepresented partly because layered discovery skip thresholds are based on raw candidate count, not fresh usable same-day candidates
- ABC and especially La Vanguardia waste extraction budget on stale/junk candidates because date filtering happens after extraction and layered discovery is not freshness-prioritized
- downstream global caps (`ENRICH_LIMIT`, `CLUSTER_LIMIT`, `SEMANTIC_LIMIT`, `SEMANTIC_BUILD_LIMIT`) amplify whichever sources dominate recent rows, which is why Explorer semantic outputs skew harder than raw scrape counts

## Specific implementer handoff
- recommended bounded slice: freshness-first candidate filtering and ordering for `abc` + `lavanguardia`
- exact aim:
  - reject obvious static asset/non-article URLs before extraction
  - use modest URL-date heuristics to prioritize same-day / near-day candidates
  - process freshest-looking candidates first so the 120 extraction slots stop getting burned on stale sitemap sludge
- likely touched areas:
  - `src/adapters/abc.py`
  - `src/adapters/lavanguardia.py`
  - `src/adapters/url_filters.py`
  - optional shared ordering hook in `src/adapters/layered_discovery.py`
  - tests: `tests/test_abc_adapter.py`, `tests/test_lavanguardia_adapter.py`, `tests/test_layered_discovery.py`
- recommended verification:
  - `pytest tests/test_abc_adapter.py tests/test_lavanguardia_adapter.py tests/test_layered_discovery.py tests/test_rss_adapter_extraction.py`
  - if env is available, compare source metrics before/after for manual runs of ABC and La Vanguardia and look for lower `discarded_by_date` + better kept/processed ratio

## Next phase
- Phase C implementer should land exactly that bounded discovery-quality fix before any broader scheduler/source-balancing work

## Prior phase summary kept for continuity
- Phase B implementer anti-bridge clustering pass completed and verified
- Phase A real Stories → Explorer story-cluster handoff completed and architect-reviewed