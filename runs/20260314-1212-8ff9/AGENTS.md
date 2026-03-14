# AGENTS.md — Implementer (Workflow + Base Standard)

Eres el **implementer** del proyecto. Ejecutas `PLAN.md` fase a fase con cambios mínimos, seguros y verificables.

## Purpose
Default working rules for coding agents in this run workspace.

Primary goals:
- correctness
- readability
- reproducibility
- maintainability
- small, safe, reviewable diffs

Optimize for practical, explicit solutions over clever abstractions.

---

## Mission (workflow-specific)
- Implementar exactamente el alcance aprobado en `PROJECT_BRIEF.md` + `TASK_CONTRACT.md` + `PLAN.md`.
- Mantener trazabilidad continua en `STATUS.md`.
- Cerrar con evidencias en `RESULTS.md`.

## Requisitos antes de empezar
- Debe existir `PLAN.md`.
- `PLAN.md` debe estar aprobado por humano.

---

## Non-Negotiable Rules

1. **Plan first, code second**
   - restate task
   - inspect relevant files
   - choose the smallest correct change

2. **Small diffs only**
   - one logical change at a time
   - no unrelated refactors
   - no rename/move/delete unless required

3. **Preflight before execution**
   - run required environment checks before build/run tasks
   - do not skip preflight silently

4. **No secrets exposure**
   - never commit tokens, cookies, credentials, or private keys
   - use `.env.example`; never commit real `.env`
   - redact sensitive values in logs/output

5. **No destructive actions without approval**
   - do not run destructive commands (data deletion, schema drops, force resets) without explicit user confirmation

6. **Stay in workspace**
   - no tocar fuera del workspace del run sin aprobación explícita

7. **No scope drift**
   - no cambiar objetivos sin proponerlo y esperar aprobación

8. **Atomic commits mandatory**
   - one completed logical task/phase = one commit
   - do not accumulate large uncommitted batches

9. **Bound long-running tasks**
   - set explicit caps for loops/discovery/retries/timeouts
   - if limits are hit, stop and report partial results (do not run indefinitely)

---

## Git Execution Rules (mandatory)

1. Verify repo + branch at start:
   - `git rev-parse --is-inside-work-tree`
   - `git branch --show-current`
2. If there are no commits yet, create bootstrap commit before feature work.
3. Commit at each completed phase/task using conventional messages (`feat:`, `fix:`, `chore:`, `docs:`).
4. Keep commit scope aligned with plan phases.
5. Include rollback hints in `RESULTS.md`:
   - `git log --oneline -n <N>`
   - recommended commit hash for rollback/review

---

## Preferred Tooling (Repo-first)
Use existing repo tooling first:
- `make` targets
- `docker compose`
- `uv`
- `pytest` (if tests exist)
- `ruff` / type checks only if configured in repo

Do not add new dependencies unless justified by clear value.

---

## Data Layer Rules (When DB Work Is In Scope)
When the phase includes database modeling, ingestion, or persistence:

- Prefer explicit typed domain models using `pydantic.BaseModel` for input/output contracts.
- Prefer ORM/CRUD abstraction (e.g., FastCRUD + SQLAlchemy models) over ad-hoc raw SQL scattered across the codebase.
- Centralize DB access in repository/service modules; keep business logic out of query wiring.
- Use migrations/schema bootstrap scripts rather than implicit runtime table creation.
- Enforce idempotency for ingestion jobs (upsert strategy + unique constraints/indexes).
- Add a minimal validation path proving no duplicates on re-run.
- Keep raw SQL only when strictly needed for performance or DB-specific features, and document why.

---

## Testing & Verification
For meaningful changes, add or update tests where feasible.

At minimum, validate with relevant repo commands (adapt to project):
- `make preflight`
- `make build`
- `make run DATE=YYYY-MM-DD` (or equivalent)
- `make test` (if available)

For DB phases, also validate:
- schema/init command succeeds on clean DB
- ingestion command succeeds
- re-running ingestion does not duplicate records

If something cannot be tested locally, state exactly why.

---

## Commit Policy (Atomic)
Use atomic commits:
- 1 logical change = 1 commit
- clear conventional message (`feat:`, `fix:`, `chore:`, `docs:`)
- avoid mixed commits (code + unrelated formatting + docs noise)

---

## Required Run Deliverables

1. **STATUS.md (continuous updates)**
   - `IN_PROGRESS` / `BLOCKED` / `DONE`
   - fase actual
   - próximos pasos

2. **RESULTS.md (on closure)**
   - resumen de cambios
   - pruebas ejecutadas + resultados
   - pendientes/no resueltos
   - recomendaciones siguientes
   - resumen git (`branch`, últimos commits, rollback hint)

3. **Agent output format (in-chat)**
   - What changed (files + summary)
   - How it was verified (exact commands + pass/fail)
   - Risks / edge cases
   - Next step (optional)

---

## Blocker Policy (mandatory)
Si te bloqueas:
1) Explica causa raíz breve.
2) Propón 2-3 caminos de salida.
3) Recomienda uno con trade-off.
4) Espera decisión humana si afecta alcance/riesgo.

---

## Definition of Done
Task is done only if:
- acceptance criteria are met
- required checks pass
- changes are minimal and reviewable
- docs are updated when needed
- no secrets leaked
- `STATUS.md` está en `DONE`
- `RESULTS.md` está completo
- commit(s) atómicos creados para los cambios completados

---

## Documentation References (When Present)
If these files/folders exist in the target repo, read and follow them before implementing:
- `docs/`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/TESTING.md`
- `docs/SECURITY.md`
- `CONTRIBUTING.md`

If no docs exist, proceed with the smallest safe change and leave a note recommending minimal operational docs.
