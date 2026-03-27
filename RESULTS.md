# RESULTS.md — iter/030 documentation cleanup, relocation, and English normalization

## Summary

iter/030 cleaned the repo docs surface without wiping history like an idiot.

The active documentation surface is now explicitly `README.md` + `docs/`, while worthwhile historical material moved into `docs/historical/` with named subfolders.

## What changed

### Root de-cluttering
Moved tracked historical docs out of repo root:
- `ARCH_AUDIT.md` → `docs/historical/audits/ARCH_AUDIT_2026-03-20.md`
- `ARCH_REVIEW.md` → `docs/historical/reviews/ARCH_REVIEW_iter-007_holistic_review.md`
- `TECH_DEBT_AUDIT.md` → `docs/historical/audits/TECH_DEBT_AUDIT_iter-015.md`
- `UI_SPEC.md` → `docs/historical/frontend/UI_SPEC_editorial_analysis_and_stories_simplification.md`
- `COMPONENT_MAP.md` → `docs/historical/frontend/COMPONENT_MAP_editorial_analysis.md`
- `DESIGN_TOKENS.md` → `docs/historical/frontend/DESIGN_TOKENS_visual_system.md`

Moved retained tracked process artifacts out of repo root:
- previous `RESULTS.md` → `docs/historical/process/RESULTS_iter-029_analysis_pipeline_refactor_phase_2.md`
- `PROJECT_STATE.json` → `docs/historical/process/PROJECT_STATE_iter-027.json`

Removed clearly worthless clutter:
- deleted `info.txt`

### Canonical docs clarification
Updated:
- `README.md`
- `docs/index.md`
- `docs/historical/index.md`
- `mkdocs.yml`

These now make the docs split explicit:
- `README.md` + `docs/` = current operator/developer truth
- `docs/historical/` = preserved reviews, audits, specs, and archived process notes

### Agent scaffolding cleanup
Relocated iter/030 scratch files out of the active root surface:
- `PROJECT_BRIEF.md` → `.agent/iter-030/PROJECT_BRIEF.md`
- `TASK_CONTRACT.md` → `.agent/iter-030/TASK_CONTRACT.md`
- `PLAN.md` → `.agent/iter-030/PLAN.md`
- deleted `TODO.md` because it was not present as meaningful retained content by the end of the pass

### English normalization
Translated the retained moved process summary at:
- `docs/historical/process/RESULTS_iter-029_analysis_pipeline_refactor_phase_2.md`

I did **not** bulk-translate every historical file just to feel productive. The retained review/audit/spec material is already mostly English, and junk that disappeared did not deserve a translation ceremony.

## Verification

1. `make docs-build`
2. fallback check: `python3 -m mkdocs build --strict`
3. manual spot-check of moved paths under `docs/historical/`
4. manual root-tree inspection to confirm the root is materially cleaner

## Verification result

- `make docs-build`: **failed in this environment** (`uv missing` from `preflight`)
- `python3 -m mkdocs build --strict`: **failed in this environment** (`No module named mkdocs`)

## Conservative calls worth noting

- `STATUS.md` stayed at repo root because the workflow for this run still expects an active status file and the task explicitly required updating it.
- `RESULTS.md` also remains active at repo root for the same reason, but the old iteration result was archived under `docs/historical/process/` so root no longer carries stale historical run output.
- `PROJECT_STATE.json` was preserved, not deleted, because it is legitimate workflow history even if it does not belong at repo root.
- local `artifacts/` research evidence was intentionally left untracked and is now ignored in `.gitignore` instead of being pulled into repo history.

## Git summary

- branch: `iter/029`
- rollback hint after review: use `git log --oneline -n 5`
