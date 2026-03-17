# ARCH_REVIEW.md

## Executive summary

This repo is **materially better than the previous review baseline**: the root is now the real app root, `uv + ruff + pytest` run successfully from root, and the scheduler/Makefile story is coherent enough to operate. That part is real, not cosmetic.

But the project is **not clean yet**. The biggest architectural drag is that archived run artifacts are still acting like semi-blessed fixtures, semi-documentation, and semi-trash heap. The codebase also has an awkward split between:
- dataclass-based domain/contracts in `src/core/*`
- Pydantic contracts in `src/persistence/*`
- SQLAlchemy ORM in `src/persistence/orm_models.py`

That separation is survivable, but right now it is only half-designed. The result is duplicated schema logic, misleading “FastCRUD-style” language without actual FastCRUD guarantees, and persistence behavior that commits one row at a time during bulk ingest.

Bottom line: **operationally usable, architecturally decent, but not yet disciplined**. The next implementation pass should focus on cleanup and repeatability, not new features.

## Scorecard

Scored 1-5.

- **Repo structure:** 3.8/5  
  Root is now canonical and runtime no longer depends on `runs/`, which is the big win. Archive hygiene is still sloppy.
- **Python/tooling discipline:** 3.2/5  
  `uv`, `ruff`, and `pytest` work. `pre-commit` is missing, caches/artifacts are noisy, and workflow enforcement is still social rather than automatic.
- **Test stability/repeatability:** 3.4/5  
  Current suite is fast and deterministic locally (`23 passed`), but it is narrow, mostly unit/fixture based, and still anchored to one archived run id.
- **Architecture/domain modeling:** 3.0/5  
  The domain is simple enough, but schema responsibilities are duplicated across custom dataclass validators and Pydantic models.
- **Persistence/API design:** 2.9/5  
  ORM and API layering are understandable, but transaction handling is weak, API behavior is barely tested, and “FastCRUD-style” is not the same as a robust CRUD boundary.
- **Operations/cron readiness:** 3.7/5  
  Makefile and scheduler are usable and mostly coherent. The scheduler has lock/retry/state, which is the right boring design. Operational artifact hygiene is still messy.

**Overall:** 3.3/5  
Good enough to run. Not clean enough to trust blindly.

## Evidence checked

Reviewed at minimum:
- `AGENTS.md`
- `PROJECT_BRIEF.md`
- `TASK_CONTRACT.md`
- `STATUS.md`
- `RESULTS.md`
- prior `ARCH_REVIEW.md`
- `pyproject.toml`
- `Makefile`
- `README.md`
- `compose.yaml`
- `scripts/run_scheduled.sh`
- `scripts/detect_app_root.sh`
- `src/**`
- `tests/**`
- `docs/**`
- `runs/**` for archive/dead-code posture only

Verification run during review:
```bash
make preflight
make lint
make test
make scheduler-dry-run
```

Observed locally:
- `make preflight` ✅
- `make lint` ✅
- `make test` ✅ (`23 passed in 0.08s`)
- `make scheduler-dry-run` ✅, but only writes to `var/log/scheduler.log`

## Prioritized findings

### Critical

#### 1) Archive hygiene is still bad enough to confuse future maintenance
**Severity:** Critical

`runs/` is no longer on the runtime path, which is good. But it still contains:
- old code copies
- tracked `__pycache__`
- nested `.venv`
- generated logs/data
- prior review docs
- run-level manifests and operational evidence

That is too much junk living too close to canonical code.

**Why this matters:**
- reviewers will keep diffing root against archive and second-guessing which copy is authoritative
- accidental edits under `runs/` remain likely
- tracked caches and generated files make git history noisy and stupid

**Evidence:**
- `runs/20260314-1212-8ff9/` still contains `src/`, `tests/`, `.venv/`, `data/`, `logs/`, `__pycache__/`, and run docs
- `git status --short` shows modifications and untracked churn inside `runs/...`, including compiled Python caches and generated logs

**Recommendation:**
Prune archive contents aggressively. Keep only evidence actually needed for traceability/contracts.

**Verification commands:**
```bash
git status --short
find runs -type d \( -name __pycache__ -o -name .venv \)
find runs -type f \( -name '*.pyc' -o -name '*.pyo' \)
```

---

#### 2) Bulk persistence is transactionally weak and operationally misleading
**Severity:** Critical

`ArticleCRUD.ingest_many()` loops row-by-row and calls `upsert()`, and `upsert()` commits every single row. That is the opposite of a clean ingest boundary.

**Why this matters:**
- partial success is guaranteed under failures, but not explicitly designed as such
- performance will degrade badly as volume grows
- repeatability is weaker because one failed row leaves a partially committed batch
- scheduler retries can re-hit partially ingested batches in awkward ways

**Evidence:**
- `src/persistence/crud.py`: `ingest_many()` iterates over rows
- `upsert()` commits immediately for inserts and updates
- `ingest_many()` catches exceptions and calls `rollback()` only after individual failures

**Recommendation:**
Refactor ingest semantics so a batch uses one explicit transaction boundary, or at least one commit per batch with documented partial-failure behavior. Right now it is neither efficient nor conceptually clean.

**Verification commands:**
```bash
python3 - <<'PY'
from pathlib import Path
p = Path('src/persistence/crud.py').read_text()
print('commit_count=', p.count('self.session.commit()'))
PY
```
After the fix, add a DB-backed test proving either:
- all-or-nothing ingest behavior, or
- intentionally documented partial-ingest behavior with counters

---

### High

#### 3) Data contracts are duplicated across incompatible styles
**Severity:** High

The project has two schema worlds:
- `src/core/contracts.py` uses custom dataclass validators with `model_validate()` / `model_dump()` methods that imitate Pydantic
- `src/persistence/contracts.py` uses real Pydantic models

That duplication is not elegant. It is a maintenance trap.

**Why this matters:**
- same conceptual entity exists in multiple representations with different validation semantics
- custom dataclass “model” APIs look like Pydantic, but are not Pydantic
- future changes will drift unless someone is extremely disciplined

**Evidence:**
- `src/core/contracts.py`
- `src/persistence/contracts.py`

**Recommendation:**
Pick one schema strategy for app-level contracts. The pragmatic choice is Pydantic for API/persistence/external payload schemas, while keeping plain dataclasses only for truly internal domain entities if they earn their keep.

**Verification commands:**
```bash
python3 - <<'PY'
from pathlib import Path
for p in ['src/core/contracts.py','src/persistence/contracts.py']:
    print('\n##', p)
    text = Path(p).read_text()
    print('model_validate count =', text.count('model_validate'))
    print('BaseModel count =', text.count('BaseModel'))
PY
```

---

#### 4) The API surface exists, but test coverage for it is basically absent
**Severity:** High

There are no API tests for:
- route wiring
- dependency injection/session lifecycle
- list/get/post/ingest behavior
- validation and status code handling

**Why this matters:**
The repo claims a small FastAPI surface, but it is effectively unverified. That’s fine for a toy, not fine for a sustainable project.

**Evidence:**
- `src/api/app.py`
- `src/api/v1/articles.py`
- no matching route tests under `tests/`

**Recommendation:**
Add API tests with `fastapi.testclient.TestClient` and an isolated test DB/session override.

**Verification commands:**
```bash
find tests -maxdepth 2 -type f | sort
python3 - <<'PY'
from pathlib import Path
print(any('TestClient' in p.read_text(encoding='utf-8') for p in Path('tests').glob('test_*.py')))
PY
```
Expected after implementation: at least one API test module and route coverage for 200/404/validation paths.

---

#### 5) `pre-commit` is missing and should be added now
**Severity:** High

The toolchain claims discipline, but there is no local guardrail preventing junk commits. That is how tracked caches, generated artifacts, and formatting drift sneak in.

**Recommendation:** yes, add it now.

**Exact hooks to add now:**
- `check-merge-conflict`
- `end-of-file-fixer`
- `trailing-whitespace`
- `check-yaml`
- `check-toml`
- `check-added-large-files`
- `ruff-check`
- `ruff-format`

If the team does **not** want formatter adoption yet, then at minimum use:
- `ruff-check`
- the five lightweight hygiene hooks above

**Verification commands:**
```bash
uv run pre-commit run --all-files
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
```

---

### Medium

#### 6) `scripts/detect_app_root.sh` is now legacy and should be removed
**Severity:** Medium

It now only verifies that `src/main.py` exists and prints `.`. That script was useful during migration. Now it is a fossil.

**Why this matters:**
Dead compatibility shims make the repo look more complex than it is.

**Evidence:**
- `scripts/detect_app_root.sh` no longer performs meaningful discovery
- repo root is already canonical by contract and implementation

**Recommendation:**
Delete it unless some external operator still calls it. If external callers exist, replace it with a one-line documented check inside the Makefile or README and then remove it.

**Verification commands:**
```bash
python3 - <<'PY'
from pathlib import Path
needle='detect_app_root.sh'
for path in sorted(Path('.').rglob('*')):
    if path.is_file() and '.git' not in path.parts and '.venv' not in path.parts:
        text = path.read_text(encoding='utf-8', errors='ignore')
        if needle in text and path.name != 'detect_app_root.sh':
            print(path)
PY
```
If that returns only docs/status/history, delete the script.

---

#### 7) Contract tests still depend on one archived run id
**Severity:** Medium

The tests are deterministic, which is good. But they are deterministic because they read one specific archived run tree: `runs/20260314-1212-8ff9`.

**Why this matters:**
- moving or pruning that run breaks tests
- archive retention policy becomes entangled with test policy
- evidence fixtures are not isolated cleanly from historical junk

**Evidence:**
- `tests/test_run_traceability.py`
- `tests/test_cross_source_output_metrics_contract.py`
- `tests/test_comparison_summary_contract.py`

**Recommendation:**
Promote only the minimal immutable evidence needed into `tests/fixtures/evidence/...` or `docs/contracts/fixtures/...`, then stop making tests depend on a whole archived run directory.

**Verification commands:**
```bash
python3 - <<'PY'
from pathlib import Path
for p in Path('tests').glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    if '20260314-1212-8ff9' in text:
        print(p)
PY
```

---

#### 8) Tooling is consistent enough, but the workflow contract is still under-specified
**Severity:** Medium

`uv`, `ruff`, and `pytest` are present and working. Good. But the repo does not yet enforce one canonical command chain like:
`uv sync && uv run ruff check ... && uv run pytest ... && uv run pre-commit run --all-files`

Also, `make scheduler-dry-run` writes only to the scheduler log. That is okay for runtime, but a little annoying for operator UX.

**Evidence:**
- `pyproject.toml` has `ruff` and `pytest` in dev group
- no `pre-commit` dependency
- no explicit CI-style aggregate target like `make check`
- `scripts/run_scheduled.sh` redirects to log file early

**Recommendation:**
Add `make check` and make it the canonical local gate. Optionally echo dry-run output to stdout as well as the log.

**Verification commands:**
```bash
make preflight
make lint
make test
```
Expected after improvement:
```bash
make check
```

---

### Low

#### 9) “FastCRUD-style” wording oversells what exists
**Severity:** Low

`ArticleCRUD` is a hand-written CRUD service, not FastCRUD. That is fine. Calling it “FastCRUD-style” is marketing copy, not architecture.

**Recommendation:**
Either:
- remove the FastCRUD language, or
- adopt a real consistent CRUD abstraction pattern with documented guarantees

**Verification commands:**
```bash
grep -R "FastCRUD-style\|FastCRUD" -n src tests README.md || true
```

---

#### 10) Stack docs are still basically empty
**Severity:** Low

`docs/STACK_CONTEXT.md` is a hollow template. That is dead documentation until proven otherwise.

**Recommendation:**
Either fill it with real operational context or delete it. Empty process theater is worse than no doc.

**Verification commands:**
```bash
sed -n '1,200p' docs/STACK_CONTEXT.md
```

## Dead-code / legacy-cleanup section

### Delete now

These are low-value legacy artifacts and should be removed in the next implementation pass if no external dependency exists:

1. **`scripts/detect_app_root.sh`**  
   It no longer discovers anything meaningful.

2. **Tracked/archive `__pycache__/` and `*.pyc` under `runs/`**  
   Pure junk. No traceability value.

3. **Nested `.venv/` directories under archived runs**  
   These are environment leftovers, not evidence.

4. **Archive-generated logs/data that are not referenced by active contract tests**  
   Keep only the minimal evidence set required for deterministic tests.

5. **Empty/template-only docs that nobody uses** like `docs/STACK_CONTEXT.md` if it remains blank.

### Keep archived, but isolate clearly

These should stay, but as explicit archive/evidence, not mixed with code archaeology:

1. **The canonical run manifest / traceability metadata** for `20260314-1212-8ff9`  
   Useful if you need provenance for the promotion.

2. **The minimal JSON evidence used by current contract tests**  
   But move it to a stable fixture location in a later cleanup pass.

3. **Historic review/planning docs only if they explain a major architectural migration**  
   Otherwise they are clutter.

### Do not delete yet

1. **`runs/20260314-1212-8ff9/run_manifest.json`**  
   Still used by traceability tests.

2. **`docs/contracts/comparison_summary.schema.json`**  
   Real contract asset, not junk.

3. **`scripts/generate_comparison_summary.py`**  
   This still has a plausible role as an operator/contract utility.

### Explicit pruning recommendation

Yes: **prune legacy artifacts now**. Keep one small archived evidence set, not an entire shadow project plus caches plus virtualenvs plus generated sludge.

## Python quality/tooling section

### Current state

What works:
- `uv sync` path is real
- `make preflight` works
- `make lint` works
- `make test` works
- `ruff` config is small and sensible

What is still weak:
- no `pre-commit`
- no aggregate `make check`
- no formatter enforcement unless manually invoked
- no explicit API or DB integration test path in standard checks
- no CI-grade artifact hygiene guardrails

### Validation result from this review

Commands run successfully:
```bash
make preflight
make lint
make test
```

Observed test result:
```text
23 passed in 0.08s
```

That is stable and fast, which is good. But it also means the suite is mostly unit/fixture validation and is not stress-testing the actual operator paths.

### Should pre-commit be added now?

**Yes. Add it now.** Waiting is dumb.

### Exact recommended `pre-commit` hooks

Use these hooks in the first pass:
- `check-merge-conflict`
- `end-of-file-fixer`
- `trailing-whitespace`
- `check-yaml`
- `check-toml`
- `check-added-large-files`
- `ruff-check`
- `ruff-format`

If the team wants zero formatting churn in the first pass, defer `ruff-format` by one commit only. Do not defer the rest.

### Recommended canonical local workflow

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
make check   # add this target
```

### Test stability / repeatability judgment

**Mostly stable, not fully representative.**

Why:
- deterministic fixture tests are good
- archived evidence tests are repeatable
- runtime/network scraping is intentionally not part of the normal test suite
- DB/API behavior is under-tested
- one archived run id is baked into tests, which is stable but brittle

## Architecture section

### Domain models

The core domain is simple: article scraping plus export plus optional persistence. That simplicity is helping the project.

`src/core/models.py` is fine as a small internal domain object. No issue there.

The real problem is the schema layer around it.

### ORM separation

The SQLAlchemy split is understandable:
- `orm_models.py` for persistence tables
- `contracts.py` for API/persistence DTOs
- `crud.py` for DB access logic
- `db.py` for engine/session wiring

That is the right rough shape. The execution is only okay.

Strengths:
- ORM model is isolated cleanly
- URL normalization to `postgresql+psycopg://` is correct
- API app uses a dependency override pattern instead of global session state

Weaknesses:
- session/transaction semantics are weak in `crud.py`
- `ArticleCRUD` mixes persistence operations with commit policy too aggressively
- there is no repository/service separation for ingest orchestration

### FastCRUD/Pydantic usage quality

**FastCRUD:** not actually present. This is a hand-rolled CRUD class. That’s fine, but say what it is.

**Pydantic:** used reasonably in `src/persistence/contracts.py`, especially `from_attributes=True` for ORM-to-read-model conversion.

**Main architectural issue:** Pydantic is not the single source of truth for schemas. `src/core/contracts.py` reimplements validation manually using dataclasses with Pydantic-like method names. That is incoherent.

### Recommendation

Pick one of these and commit to it:

#### Option A — recommended
- Keep `src/core/models.Article` as a plain internal dataclass
- Use Pydantic for all external/input-output/schema contracts
- Remove custom pseudo-Pydantic contract classes from `src/core/contracts.py` over time

#### Option B
- Keep custom dataclass validators only for pure contract fixtures and export validation
- But rename them so they stop pretending to be Pydantic

**Option A is cleaner.**

### Acceptance checks for architectural cleanup

```bash
python3 - <<'PY'
from pathlib import Path
print(Path('src/core/contracts.py').exists())
print(Path('src/persistence/contracts.py').exists())
PY
```
After cleanup, there should be a clearly documented reason for both layers, or one should be retired.

## Operations section

### Makefile quality

The Makefile is honestly pretty solid now.

What it gets right:
- root-first assumptions are consistent
- `uv` is the canonical runner
- targets are understandable
- local DB path is optional, not forced
- scheduler/verify targets exist

What still needs tightening:
- no `make check`
- no `make pre-commit`
- `scheduler-dry-run` gives no stdout feedback because the script redirects logs early
- `clean-state` is weakly named and not very meaningful

### Scheduler / cron readiness

The scheduler design is the right boring shape:
- `flock` anti-overlap ✅
- retry loop ✅
- state files ✅
- optional alert hook ✅
- log file ✅

That is better than shoving APScheduler into a repo that doesn’t need it.

Concerns:
- dry-run UX is awkward
- scheduler log contains stale historical lines from pre-root promotion runs, including obsolete app-root references
- alerting is generic and untested
- there is no documented log rotation strategy

### Cron recommendation

**Cron is still the correct default.** No need for a Python scheduler. No need for Celery. No need for infrastructure cosplay.

Recommended production-ish cron pattern remains reasonable, but it should be paired with:
- explicit log rotation outside the repo, or
- documented truncation/rotation policy for `var/log/scheduler.log`

### Acceptance checks for operations

```bash
make scheduler-dry-run
make status
bash scripts/run_scheduled.sh   # with DATABASE_URL set in a safe test environment
```

For overlap behavior:
```bash
flock -n var/lock/spain-news-bias-scraper.lock true && echo ok
```

For DB verification path:
```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make verify-db
```

## Recommended phased plan

### Phase 1 — Hygiene and guardrails
**Goal:** stop repository rot.

Tasks:
- add `pre-commit`
- add `make check`
- extend `.gitignore` / cleanup policy for archive junk if still needed
- stop tracking caches/compiled files under `runs/`
- decide whether `docs/STACK_CONTEXT.md` is real or dead

Acceptance checks:
```bash
uv run pre-commit run --all-files
make check
find runs -type d -name __pycache__
find runs -type f \( -name '*.pyc' -o -path '*/.venv/*' \)
```

### Phase 2 — Evidence isolation
**Goal:** keep deterministic tests without keeping a landfill.

Tasks:
- move active evidence fixtures out of `runs/20260314-1212-8ff9` into a stable fixture directory
- update contract tests to use fixture paths, not archived run paths
- keep one archived manifest only if traceability still matters

Acceptance checks:
```bash
python3 - <<'PY'
from pathlib import Path
for p in Path('tests').glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    assert '20260314-1212-8ff9' not in text, p
print('ok')
PY
make test
```

### Phase 3 — Persistence semantics cleanup
**Goal:** make ingest behavior sane.

Tasks:
- refactor `ArticleCRUD` commit policy
- define explicit batch-ingest transaction behavior
- add DB-backed tests for insert/update/unchanged/error scenarios

Acceptance checks:
```bash
make test
# plus new DB-backed tests
```
Expected proof points:
- ingest behavior documented
- failure semantics tested
- commit frequency no longer one-per-row

### Phase 4 — API confidence
**Goal:** make the FastAPI surface real, not decorative.

Tasks:
- add route tests
- validate 200/404/422 flows
- verify dependency override/session lifecycle

Acceptance checks:
```bash
make test
python3 - <<'PY'
from pathlib import Path
print(any('TestClient' in p.read_text(encoding='utf-8') for p in Path('tests').glob('test_*.py')))
PY
```

### Phase 5 — Final archive pruning
**Goal:** leave only meaningful history.

Tasks:
- delete `scripts/detect_app_root.sh` if unused
- prune archived code copies/caches/envs not required for evidence
- document what remains in `runs/` and why

Acceptance checks:
```bash
git status --short
find runs -type d \( -name __pycache__ -o -name .venv \)
```

## Top 5 concrete issues

1. `ingest_many()` commits via `upsert()` one row at a time, which is weak transaction design.
2. Tests still depend on archived run `runs/20260314-1212-8ff9` instead of isolated fixtures.
3. `pre-commit` is missing, so repository hygiene is not enforced.
4. `scripts/detect_app_root.sh` is legacy baggage and should be removed if unused.
5. Schema/contracts are duplicated across custom dataclass validators and Pydantic models.

## Top 5 highest-ROI improvements

1. Add `pre-commit` with hygiene + Ruff hooks.
2. Add `make check` as the one local verification command.
3. Move test evidence out of `runs/...` into stable fixtures.
4. Refactor batch ingest transaction handling and add DB-backed tests.
5. Prune `runs/` aggressively: remove tracked caches, nested venvs, and dead archive sludge.

## Final recommendation

This project does **not** need a rewrite. It needs discipline.

The repo is now credible as a root-first Python project. Good. Don’t waste that progress by keeping archive junk, weak ingest semantics, and unenforced tooling standards around forever. The highest-value next step is boring cleanup with hard acceptance checks.

## Post-phase acceptance (2026-03-15)

### Accepted improvements

This phase fixed the two biggest issues from the prior review:
- **Batch ingest semantics are now materially better.** `ArticleCRUD.ingest_many()` no longer commits one row at a time; it commits once per batch and explicitly rolls back on SQLAlchemy failure.
- **Persistence behavior now has real DB-backed tests.** `tests/test_persistence_crud.py` covers insert, update, unchanged/idempotent behavior, and rollback-on-failure.
- **The API surface is no longer decorative.** `tests/test_api_articles.py` covers 200 / 404 / 422 paths and verifies dependency-driven session closing.
- **Fixture isolation improved.** Active contract tests now read from `tests/fixtures/evidence/...` instead of depending on the archived run tree as live test input.
- **Tooling discipline improved on paper.** `pre-commit`, `make check`, and the root-first workflow are now defined in repo config and docs.

### Remaining risks / gaps

- **Acceptance gate is not actually clean yet.** During this review, `make check` failed on the first run because `ruff-check` found E501 issues in `tests/test_persistence_crud.py` and `ruff-format` then rewrote files. That means the claimed canonical gate was not green from a fresh checkout state.
- **Repo hygiene is still messy outside the narrow phase scope.** There is still substantial churn under `runs/`, and the working tree still shows archived logs/docs noise and tracked historical artifacts. Better than before, still not disciplined.
- **The new persistence/API confidence is SQLite-based, not Postgres-backed.** That is acceptable for fast local coverage, but it does not prove dialect-specific behavior, transaction edges, or migration assumptions against the real target DB.

### Recommended next small changes

1. **Make `make check` truly boring and green from a clean tree.** Re-run `uv run pre-commit run --all-files`, commit the resulting formatting, and verify `make check` passes without mutating files.
2. **Do one small Postgres smoke path for persistence/API.** Not a huge CI buildout—just one documented or scripted verification proving the real target dialect still behaves.
3. **Continue pruning `runs/` noise separately.** The code is now ahead of the archive mess; don’t let the archive keep pretending to be part of the product.

### Acceptance verdict

**Accept with minor follow-ups.**

Why: the substantive implementation work is good enough to accept, and the previous critical persistence/API gaps are now addressed. But calling the phase fully solid before the canonical gate is clean would be bullshit.
