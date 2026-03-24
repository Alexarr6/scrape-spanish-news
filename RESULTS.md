## 2026-03-24 — iter/008 explorer article-type editorial lens backend

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** bounded backend/data slice for Explorer article-type editorial lenses

### What I accomplished
- added lightweight `editorial_preview` onto Explorer points/contracts
  - payload includes `analysis_status`, `editorial_applicability`, `article_type`, `article_type_confidence`, and review flags
  - intentionally avoids full rationale/evidence blobs so point-cloud responses stay light
- added editorial query support on `/api/v1/semantic/explorer/points`
  - `sem_editorial_dim=article_type`
  - `sem_editorial_value=<label>`
- implemented mode behavior
  - `sem_mode=filter` applies article-type narrowing at query time
  - `sem_mode=highlight` leaves the dataset broad and still returns previews for all points
- added bounded Explorer editorial metadata
  - article-type option counts
  - coverage counts for `total`, `pending`, `failed`, `unknown`, `limited`, `out_of_domain`
- aligned shared frontend TS types with the backend contract additions
- expanded targeted semantic explorer API tests for preview payloads, article-type filter/highlight behavior, and editorial meta payloads

### Files changed
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/contracts.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- `frontend/src/lib/types.ts`
- `STATUS.md`
- `RESULTS.md`

### Verification
Commands run:
- `python3 -m py_compile src/api/contracts/semantic.py src/api/v1/semantic.py src/semantic/contracts.py src/semantic/dbstore.py tests/test_api_semantic_explorer.py`
- `/home/node/.local/bin/uv run --group dev python -m pytest tests/test_api_semantic_explorer.py`

Results:
- py_compile: passed
- semantic explorer pytest slice: passed (`12 passed`)

### Review notes / frontend handoff
- Explorer point payloads now expose `editorial_preview`; the frontend can use that for point coloring/highlighting/tooltips without fetching article detail
- `/filters` and `/points.meta` now expose bounded `editorial` metadata for article-type options/counts
- only `article_type` lensing is implemented in this slice; bias/tone lenses were intentionally deferred
