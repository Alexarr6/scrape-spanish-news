# TECH_DEBT_AUDIT.md — iter/015

Date: 2026-03-26  
Scope: frontend, backend, scripts, contracts/docs alignment, generated/runtime clutter, Makefile/tooling

This audit is intentionally evidence-first. The repo does have cleanup opportunities, but a giant "delete all the ugly stuff" pass would be reckless bullshit. The useful split is:

- things that are actually dead
- things that are live but clumsy
- things that smell dead but still need operator/runtime proof
- things that are real debt but should wait for a bounded refactor lot

---

## Audit method used

Evidence sources used in this pass:

1. live entrypoints and operator wiring
   - `Makefile`
   - `README.md`
   - `mkdocs.yml`
   - `src/main.py`
   - `src/api/app.py`
   - shell wrappers in `scripts/`
2. structural reference checks
   - Python import graph scan across `src/`, `scripts/`, `tests/`
   - frontend import graph scan across `frontend/src/`
   - repo-wide string/reference checks for suspicious files
3. docs and operator contract checks
   - docs nav vs tracked docs vs untracked docs
   - Makefile help text vs actual targets
4. generated/runtime clutter check
   - ignored build outputs, caches, local envs, runtime artifacts, untracked leftovers

Important constraint honored here: grep alone was not treated as proof when stronger runtime or wiring evidence existed.

---

## Executive summary

The repo’s debt is concentrated in **five** buckets:

1. **Confirmed dead leaf files**
   - a few frontend hooks and Python compatibility/strategy leaves are genuinely unwired
2. **Generated/config byproducts and runtime clutter**
   - frontend emitted config artifacts, tsbuildinfo, `frontend/dist/`, `site/`, caches, local artifacts, data/log churn
3. **Tooling/operator surface debt**
   - Makefile is broadly useful, but it still mixes canonical targets with legacy scheduler affordances and a couple of contract mismatches
4. **Docs/operator drift**
   - docs are mostly decent, but scheduler/workflow/output docs disagree on what is canonical and which state files exist
5. **Large live modules that need bounded simplification, not random surgery**
   - `src/analysis/pipeline.py`, `src/analysis/readside.py`, `src/semantic/dbstore.py`, `src/semantic/export.py`, plus frontend URL-state/navigation splits

My blunt read: the repo is not drowning in dead code. The bigger issue is **surface sprawl and contract drift**, especially around tooling/docs and around frontend/backend state orchestration.

---

## Findings

## Confirmed findings table

| ID | Surface | Location(s) | Issue type | Evidence summary | Classification | Verification / check | Recommended lot |
|---|---|---|---|---|---|---|---|
| TD-001 | frontend | `frontend/src/hooks/useClusterFilters.ts` | dead code | zero in-repo importers from frontend graph scan; only self-definition reference | safe delete | `grep -RIn "useClusterFilters" frontend/src` | Lot 2C |
| TD-002 | frontend | `frontend/src/hooks/useExplorerBootstrap.ts` | dead code | zero in-repo importers; app uses `useExplorerData` instead | safe delete | `grep -RIn "useExplorerBootstrap" frontend/src` | Lot 2C |
| TD-003 | frontend | `frontend/src/hooks/useExplorerFilters.ts` | dead code | zero in-repo importers; explorer uses URL-state/data hooks instead | safe delete | `grep -RIn "useExplorerFilters" frontend/src` | Lot 2C |
| TD-004 | backend | `src/core/strategies/rss_discovery.py` | dead code | zero Python importers in repo; only test fixture strings mention `rss_discovery` by name, not module/class wiring | safe delete | `grep -RIn "rss_discovery" src tests scripts` | Lot 2B |
| TD-005 | backend/contracts | `src/persistence/contracts.py` | compatibility barrel / dead re-export | zero Python importers; repo imports come from `src.persistence.core`; remaining mentions are docs/archive/log strings | safe delete | `grep -RIn "src\.persistence\.contracts\|from src\.persistence\.contracts" src tests scripts docs README.md Makefile` | Lot 2B |
| TD-006 | generated | `frontend/vite.config.js`, `frontend/vite.config.d.ts`, `frontend/tsconfig.app.tsbuildinfo`, `frontend/tsconfig.node.tsbuildinfo` | generated clutter | source of truth is `frontend/vite.config.ts`; generated files are ignored by `frontend/.gitignore`; not tracked in git | safe delete | `git ls-files frontend | egrep 'vite\.config\.(js|d\.ts)|tsconfig\..*\.tsbuildinfo'` should stay empty | Lot 2A |
| TD-007 | docs/clutter | untracked `docs/architecture/2026-03-24-explorer-bias-lens-architecture.md`; untracked `docs/reviews/2026-03-24-iter-009-explorer-bias-lens-review.md` | leftover docs clutter | present as untracked files; not in `git ls-files docs`; not in `mkdocs.yml` nav | safe delete | `git status --short docs/architecture docs/reviews` | Lot 2A |
| TD-008 | tooling | `Makefile` | contract mismatch | `frontend-install`, `frontend-build`, `frontend-check` exist as real targets and are referenced in README/docs, but are missing from `.PHONY` and from the advertised help block | safe simplify | `make help`; inspect `.PHONY`; run `make frontend-build` after edit | Lot 2D |
| TD-009 | docs/operator | `docs/operator-guide/workflows.md`, `docs/operator-guide/scheduler.md`, `README.md`, `Makefile` | docs contract drift | workflow doc still says supported scheduler entrypoint is `run_scheduled.sh`; README and scheduler doc say new canonical wrappers are `run_stories_refresh.sh` / `run_explorer_refresh.sh` / `make full-refresh-once` | safe simplify | `make help` + read docs pages side by side | Lot 4B |
| TD-010 | docs/operator | `docs/reference/outputs.md` vs `docs/operator-guide/scheduler.md` | docs drift | outputs reference documents only legacy `var/state/last_*`; scheduler doc documents per-job `stories_*` and `explorer_*` state files | safe simplify | `grep -RIn "stories_last_status\|explorer_last_status\|last_status" docs` | Lot 4B |
| TD-011 | frontend | `frontend/src/App.tsx`, `frontend/src/hooks/useClusterUrlState.ts`, `frontend/src/hooks/useExplorerUrlState.ts`, `frontend/src/lib/navigation.ts` | duplicated active patterns / navigation debt | app surface switch still relies on query-param mode switching; two separate URL-state systems exist; prior review already flagged fake-router/back-button debt | defer | manual browser verification + eventual route-based refactor | Lot 3A |
| TD-012 | backend/api | `src/analysis/readside.py` | oversized live module | 1358 LOC; handles query assembly, summaries, detail shaping, filter loading; active import surface so not dead, but becoming a god-file | defer | preserve API contract while extracting readside slices later | Lot 3B |
| TD-013 | backend/analysis | `src/analysis/pipeline.py` | oversized live module | 2257 LOC; active, heavily imported, test-covered; debt is complexity, not deadness | defer | bounded extraction with focused pytest subsets | Lot 3B |
| TD-014 | backend/semantic | `src/semantic/dbstore.py` | oversized live module | 1884 LOC; central persistence/query surface; previous reviews already flagged N+1 and growth pattern | defer | semantic test subset + operator smoke after changes | Lot 3B |
| TD-015 | backend/semantic | `src/semantic/export.py` | active but overgrown export/UI glue | 628 LOC with HTML/script generation; prior review explicitly called out giant function risk | needs verification | check whether current split pain is review-only or already slowing feature work | Lot 3B |
| TD-016 | scripts | `scripts/bootstrap_story_gold_set.py`, `scripts/compare_story_thresholds.py`, `scripts/evaluate_story_matching.py`, `scripts/prepare_story_review_batch.py`, `scripts/summarize_story_review_feedback.py` | suspicious low-surface scripts | not wired from Makefile, README, or tests; only architecture docs mention them | needs verification | confirm whether story-matching eval workflow is still an active operator surface | Lot 3C / 4B |
| TD-017 | tooling | legacy scheduler family: `scheduler-dry-run`, `scheduler-once`, `status`, `tail-log`, `scripts/run_scheduled.sh` | legacy operator surface clutter | explicitly marked legacy in Makefile/README/docs, but still present in primary help and docs because they remain runnable | needs verification | confirm whether any cron/operator still depends on legacy scrape-only wrapper | Lot 4A |
| TD-018 | runtime clutter | `.artifacts/`, `artifacts/`, `data/`, `logs/`, `var/`, `frontend/dist/`, `frontend/node_modules/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `site/` | generated/runtime clutter | mostly ignored and untracked; repo root currently has a lot of local operational noise that can obscure audit signal even if git ignores it | needs verification | define retention policy before deleting nontrivial artifacts | Lot 2A / 4B |

---

## Confirmed-dead appendix

These have deletion-grade evidence right now.

### A. Frontend dead hooks

1. `frontend/src/hooks/useClusterFilters.ts`
2. `frontend/src/hooks/useExplorerBootstrap.ts`
3. `frontend/src/hooks/useExplorerFilters.ts`

Why this is confirmed dead:
- frontend import graph scan found zero in-repo importers for all three
- app wiring goes through:
  - `useClusterBrowserData`
  - `useClusterUrlState`
  - `useExplorerData`
  - `useExplorerUrlState`
- no route/component imports them

Risk note:
- low; these are leaf hooks, not shared type files or runtime config

### B. Python dead/compat leaves

1. `src/core/strategies/rss_discovery.py`
2. `src/persistence/contracts.py`

Why this is confirmed dead:
- Python import graph scan found zero in-repo importers
- remaining matches are docs/archive/log text, not live code wiring
- `src/persistence.core` is the actual live contract import surface

Risk note:
- low to medium-low; safe if cleanup lot also updates stale docs references where appropriate

### C. Generated frontend config byproducts

1. `frontend/vite.config.js`
2. `frontend/vite.config.d.ts`
3. `frontend/tsconfig.app.tsbuildinfo`
4. `frontend/tsconfig.node.tsbuildinfo`

Why this is confirmed clutter:
- canonical source file is `frontend/vite.config.ts`
- `frontend/.gitignore` already ignores these emitted byproducts
- `git ls-files` shows they are not tracked

Risk note:
- trivial; they are recreatable

### D. Untracked doc leftovers

1. `docs/architecture/2026-03-24-explorer-bias-lens-architecture.md`
2. `docs/reviews/2026-03-24-iter-009-explorer-bias-lens-review.md`

Why this is confirmed clutter:
- untracked in git status
- absent from tracked docs list
- absent from `mkdocs.yml` nav
- functionally invisible to the canonical docs site

Risk note:
- low; these are exactly the kind of leftovers that make a repo feel haunted

---

## Suspicious-but-unconfirmed appendix

These smell stale, but deleting them without one more verification step would be sloppy.

### S-001 — story-matching/eval scripts outside operator surface

Suspicious files:
- `scripts/bootstrap_story_gold_set.py`
- `scripts/compare_story_thresholds.py`
- `scripts/evaluate_story_matching.py`
- `scripts/prepare_story_review_batch.py`
- `scripts/summarize_story_review_feedback.py`

Why they look suspicious:
- not wired through `Makefile`
- not mentioned in `README.md`
- not referenced in tests
- only referenced from architecture/story-eval docs

Why not confirmed dead yet:
- these could still be intentionally manual analyst tools
- docs do describe a workflow around them, so deleting now would be optimism disguised as engineering

What would convert this to safe delete or safe document:
- explicit operator decision: keep as manual research tools vs archive/remove
- if kept, they need one documented execution surface and one verification command

### S-002 — legacy scheduler surface

Suspicious items:
- `make scheduler-dry-run`
- `make scheduler-once`
- `make status`
- `make tail-log`
- `scripts/run_scheduled.sh`

Why they look stale:
- help text and docs label them legacy/deprecated
- product docs increasingly point at `stories-refresh-once`, `explorer-refresh-once`, and `full-refresh-once`

Why not confirmed dead yet:
- still runnable
- still documented
- old cron or operator habits may still depend on them

What would convert this to safe delete/merge:
- verify no active cron/operator dependency remains
- if retained, move them out of the primary happy-path help surface

### S-003 — runtime artifacts and local operational noise

Suspicious areas:
- `.artifacts/`
- `artifacts/`
- `data/`
- `logs/`
- `var/`

Why they matter:
- not all clutter is junk; some is current run evidence
- but without retention rules, these directories become an accidental landfill

Why not safe-delete by default:
- some files may be actively useful for recent validation or manual review

What would convert this to safe cleanup:
- retention policy by directory
- explicit keep/drop rules for recent run windows, review artifacts, and semantic outputs

---

## Makefile and tooling audit

## Overall verdict

The Makefile is **mostly the right operator surface**. It is not a graveyard, but it does have some operator-UI debt:

- canonical runtime and analysis targets are clear
- frontend targets exist but are under-advertised
- legacy scheduler targets still occupy premium help-space real estate
- docs do not fully agree on which scheduler path is canonical

### Target family audit

#### 1. Bootstrap / quality targets
- `sync`, `preflight`, `lint`, `pre-commit`, `check`, `test`, `docs-build`, `docs-serve`
- Verdict: **keep**
- Reason: clear, useful, aligned with README/docs
- Debt: frontend quality targets should sit here too, not half-hidden outside help and `.PHONY`

#### 2. Frontend targets
- `frontend-install`, `frontend-build`, `frontend-check`
- Verdict: **keep, but simplify/document**
- Evidence:
  - real targets exist
  - README references `make frontend-build` / `make frontend-check`
  - docs/operator-guide/commands.md references them too
  - `.PHONY` omits them
  - help output omits them
- Fix shape:
  - add them to `.PHONY`
  - list them in the Bootstrap/API section of help output

#### 3. Scrape/runtime targets
- `smoke`, `run-source`, `run-source-persist`, `run-all`, `run-all-persist`, `api`
- Verdict: **keep**
- Reason: canonical runtime surface is coherent

#### 4. Analysis / semantic targets
- `analysis-db-init`, `enrich-articles`, `build-matching-corpus`, `analyze-editorial`, `analyze-editorial-failed`, `build-story-clusters`, `story-cluster-report`, `semantic-db-init`, `semantic-sync`, `semantic-project`, `semantic-neighbors`, `semantic-build`, `semantic-smoke`
- Verdict: **keep**
- Reason: current docs and code agree these are the live pipeline surface
- Debt:
  - a few research/eval scripts sit outside this surface with unclear status

#### 5. Legacy scheduler targets
- `scheduler-dry-run`, `scheduler-once`, `status`, `tail-log`
- Verdict: **verify first / probably demote later**
- Reason:
  - explicitly labeled legacy
  - still in primary help output
  - still mentioned in docs
- Best next move:
  - do not delete blindly
  - either demote to a clearly marked legacy section or remove once operator usage is confirmed absent

#### 6. New orchestration targets
- `stories-refresh-once`, `explorer-refresh-once`, `full-refresh-once`
- Verdict: **keep and treat as canonical**
- Reason: README and scheduler docs clearly prefer them
- Debt: workflows docs still lag behind and muddy the story

#### 7. Verification and DB helper targets
- `verify-output`, `verify-db`, `db-url`, `db-up`, `db-down`, `db-logs`, `db-psql`, `db-check`
- Verdict: **keep**
- Reason: operator helpers are boring and useful

#### 8. `clean-state`
- Verdict: **needs verification**
- Reason:
  - real but narrow utility
  - only touches `var/state`/`var/lock`
  - not documented in help output
- Possible outcome:
  - either document it properly or fold it into a clearer maintenance target family

### Concrete Makefile/tooling findings

#### M-001 — missing `.PHONY` coverage for real frontend targets
Classification: `safe simplify`

Why it matters:
- these are real human-facing targets
- lack of `.PHONY` coverage is not catastrophic, but it is sloppy

#### M-002 — help surface under-advertises frontend build/check
Classification: `safe simplify`

Why it matters:
- docs/README point people to targets that `make help` does not advertise
- operator surface should not force people to read three documents to discover supported commands

#### M-003 — legacy scheduler surface still occupies top-level operator real estate
Classification: `needs verification`

Why it matters:
- the repo now has a newer split refresh model
- keeping deprecated targets in prime help-space preserves confusion longer than necessary

#### M-004 — docs do not agree on canonical scheduler entrypoint
Classification: `safe simplify`

Why it matters:
- this is the exact sort of contract drift that causes needless operator mistakes

---

## Contracts/docs alignment audit

## What aligns well
- `README.md` largely matches current Makefile/runtime reality
- `docs/index.md` correctly treats Makefile, package manifests, app entrypoints, and tests as truth sources
- semantic docs are generally aligned with current projection/export flow

## Drift that needs cleanup

### D-001 — scheduler canon is inconsistent
- `README.md`: prefers new orchestration wrappers and marks legacy scrape-only path as deprecated
- `docs/operator-guide/scheduler.md`: same story
- `docs/operator-guide/workflows.md`: still says "The supported scheduler entrypoint is: bash scripts/run_scheduled.sh"

Verdict: `safe simplify`

### D-002 — outputs/state docs are legacy-only
- `docs/reference/outputs.md` documents only legacy scheduler state files (`last_status`, `last_run_utc`, etc.)
- current scheduler doc describes per-job `stories_*` and `explorer_*` state files

Verdict: `safe simplify`

### D-003 — untracked docs leftovers outside nav
- two untracked docs files exist outside canonical docs nav and git tracking

Verdict: `safe delete`

---

## Generated/runtime clutter audit

## Confirmed local/generated clutter
- `frontend/vite.config.js`
- `frontend/vite.config.d.ts`
- `frontend/tsconfig.app.tsbuildinfo`
- `frontend/tsconfig.node.tsbuildinfo`
- `frontend/dist/`
- `frontend/node_modules/`
- `.venv/`
- `.pytest_cache/`
- `.ruff_cache/`
- `site/`

These are either ignored explicitly in `.gitignore` / `frontend/.gitignore` or obviously generated outputs.

## Operational clutter needing retention rules
- `artifacts/`
- `.artifacts/`
- `data/`
- `logs/`
- `var/`

These are not automatically junk. The real debt is lack of an explicit keep/prune policy.

---

## Recommended bounded cleanup lots

## Lot 2A — generated/config byproducts + untracked leftovers
**Scope**
- delete generated frontend config byproducts and tsbuildinfo
- delete clearly untracked docs leftovers
- document what generated directories are intentionally ignored

**Expected files**
- `frontend/vite.config.js`
- `frontend/vite.config.d.ts`
- `frontend/tsconfig.app.tsbuildinfo`
- `frontend/tsconfig.node.tsbuildinfo`
- untracked docs leftovers under `docs/architecture/` and `docs/reviews/`

**Risk**: low  
**Verification**
- `git status --short`
- `cd frontend && npm run build`
- `make docs-build`

**Stop condition**
- if any supposedly generated file is discovered to be a manual source of truth, stop immediately

## Lot 2B — confirmed dead Python leaves
**Scope**
- remove confirmed dead Python leaf modules
- update stale docs references only if directly touched by the deletion

**Expected files**
- `src/core/strategies/rss_discovery.py`
- `src/persistence/contracts.py`

**Risk**: low to medium-low  
**Verification**
- `make test`
- focused grep/reference check for removed imports

**Stop condition**
- if runtime import errors or hidden external script usage appears, revert and reclassify

## Lot 2C — confirmed dead frontend hooks
**Scope**
- remove dead leaf hooks

**Expected files**
- `frontend/src/hooks/useClusterFilters.ts`
- `frontend/src/hooks/useExplorerBootstrap.ts`
- `frontend/src/hooks/useExplorerFilters.ts`

**Risk**: low  
**Verification**
- `cd frontend && npm run build`

**Stop condition**
- if any route/component unexpectedly imports one during cleanup, stop and keep it

## Lot 2D — Makefile hygiene fixes
**Scope**
- add missing frontend targets to `.PHONY`
- expose frontend targets in help
- keep behavior unchanged

**Expected files**
- `Makefile`
- maybe `README.md` / docs only if help wording needs alignment

**Risk**: low  
**Verification**
- `make help`
- `make frontend-build`

**Stop condition**
- if any target rename or semantic behavior change sneaks in, split it into a later lot

## Lot 3A — frontend navigation/state normalization
**Scope**
- route split / state ownership cleanup
- reduce fake-router query-param switching
- avoid mixing with major visual redesign

**Expected files**
- `frontend/src/App.tsx`
- `frontend/src/hooks/useClusterUrlState.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/lib/navigation.ts`
- route files under `frontend/src/routes/`

**Risk**: medium  
**Verification**
- `cd frontend && npm run build`
- manual back/forward and handoff checks

**Stop condition**
- if this starts becoming a full app-shell rewrite, cut scope

## Lot 3B — backend module boundary cleanup
**Scope**
- extract bounded subsurfaces from oversized live modules
- no behavior change chase, no mega-refactor vanity

**Priority files**
- `src/analysis/readside.py`
- `src/analysis/pipeline.py`
- `src/semantic/dbstore.py`
- `src/semantic/export.py`

**Risk**: medium  
**Verification**
- targeted pytest subsets by subsystem
- `make test`

**Stop condition**
- if any lot touches more than one major subsystem without need, split again

## Lot 3C — script-surface triage
**Scope**
- decide whether story-matching/eval scripts are active manual tools, archive material, or dead code
- do not delete them until operator intent is explicit

**Expected files**
- story-matching/eval scripts under `scripts/`
- related docs under `docs/architecture/story-matching-eval.md`

**Risk**: medium  
**Verification**
- prove one real execution path if kept
- otherwise archive/remove with docs cleanup

**Stop condition**
- if operator ownership remains unclear, leave them documented as manual/research tools and move on

## Lot 4A — legacy scheduler surface cleanup
**Scope**
- demote or remove legacy scheduler wrapper/targets after verification
- preserve one obvious canonical path

**Expected files**
- `Makefile`
- `scripts/run_scheduled.sh`
- scheduler docs

**Risk**: medium  
**Verification**
- confirm no active cron/operator dependence first
- `make help`
- wrapper `--`/dry-run checks as applicable

**Stop condition**
- if any real deployment still depends on legacy wrapper, keep but quarantine clearly

## Lot 4B — docs/operator contract alignment
**Scope**
- align scheduler/workflow/output docs with surviving command surface
- remove leftover misleading docs paths

**Risk**: low to medium  
**Verification**
- `make docs-build`

**Stop condition**
- do not rewrite docs architecture history; only align active operator contracts

---

## Recommended next action order

1. **Lot 2A** — cheap, obvious clutter win
2. **Lot 2C** — dead frontend hooks
3. **Lot 2B** — dead Python leaves
4. **Lot 2D** — Makefile hygiene
5. **Lot 4B** — docs alignment for scheduler/output truth
6. **Lot 3A / 3B / 3C** — only after low-risk wins are done
7. **Lot 4A** — legacy scheduler pruning after operator verification

---

## Final verdict

The repo does have real debt, but the low-risk cleanup queue is not huge. That’s actually good news.

The smartest immediate work is not a macho repo-wide purge. It is:
- kill the genuinely dead leaves
- delete the fake-source generated junk
- tighten the Makefile/help/docs contract
- then go after the big live-module and navigation debt in bounded slices

That path reduces maintenance cost without turning the branch into a bonfire.