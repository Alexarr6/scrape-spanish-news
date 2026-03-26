# RESULTS.md — iter/015 technical-debt audit

## Resumen breve

Iter/015 no hizo una limpieza masiva. Hizo algo más útil: dejó un **mapa de deuda técnica con evidencia**, separado por riesgo y por lotes ejecutables.

Entregables principales:
- auditoría repo-wide en `TECH_DEBT_AUDIT.md`
- clasificación explícita por:
  - `safe delete`
  - `safe simplify`
  - `needs verification`
  - `defer`
- distinción clara entre **muerto confirmado** y **sospechoso pero no confirmado**
- auditoría real de Makefile/tooling
- plan de siguientes lotes acotados para ejecutar después sin improvisar

## Qué se auditó

Superficies revisadas:
- backend Python (`src/`, `scripts/`, `tests/`)
- frontend (`frontend/src/` + config)
- contratos/API/docs
- Makefile/tooling (`Makefile`, `pyproject.toml`, `mkdocs.yml`, `compose.yaml`, pre-commit, frontend package/config)
- clutter generado/runtime (`site/`, `frontend/dist/`, tsbuildinfo, caches, artifacts, docs sueltas no enlazadas, etc.)

Método aplicado:
- entrypoints reales antes que grep barato
- import graph básico en Python y frontend
- comparación entre Makefile, README y docs
- comprobación de tracking/nav para distinguir fuente canónica vs residuo

## Hallazgos importantes

### Confirmado como deuda de borrado fácil (`safe delete`)

#### Frontend hooks muertos
- `frontend/src/hooks/useClusterFilters.ts`
- `frontend/src/hooks/useExplorerBootstrap.ts`
- `frontend/src/hooks/useExplorerFilters.ts`

Evidencia:
- el escaneo de imports del frontend dio **0 importadores** para los tres
- las rutas activas usan otros hooks (`useClusterBrowserData`, `useClusterUrlState`, `useExplorerData`, `useExplorerUrlState`)

#### Hojas Python muertas / barrels fósiles
- `src/core/strategies/rss_discovery.py`
- `src/persistence/contracts.py`

Evidencia:
- el escaneo de imports Python dio **0 importadores en repo**
- las referencias restantes son docs, strings históricas o logs, no wiring activo

#### Clutter generado claro
- `frontend/vite.config.js`
- `frontend/vite.config.d.ts`
- `frontend/tsconfig.app.tsbuildinfo`
- `frontend/tsconfig.node.tsbuildinfo`

Evidencia:
- la fuente real es `frontend/vite.config.ts`
- `frontend/.gitignore` ya los trata como generados
- no están tracked por git

#### Docs sueltas no canónicas
- `docs/architecture/2026-03-24-explorer-bias-lens-architecture.md`
- `docs/reviews/2026-03-24-iter-009-explorer-bias-lens-review.md`

Evidencia:
- están untracked
- no aparecen en `mkdocs.yml`
- no forman parte del sitio canónico

### `safe simplify`

#### Makefile / tooling
- `frontend-install`, `frontend-build`, `frontend-check` existen pero no están en `.PHONY`
- esos targets existen y salen en README/docs, pero `make help` no los anuncia

Esto no es drama, pero sí deuda tonta. Fácil de arreglar sin cambiar comportamiento.

#### Drift documental claro
- `docs/operator-guide/workflows.md` sigue vendiendo `run_scheduled.sh` como entrypoint soportado
- README + `docs/operator-guide/scheduler.md` ya dejan claro que lo canónico son:
  - `run_stories_refresh.sh`
  - `run_explorer_refresh.sh`
  - `make full-refresh-once`
- `docs/reference/outputs.md` documenta solo el estado legacy y no el estado por job (`stories_*`, `explorer_*`)

### `needs verification`

#### Scripts de story-matching / review batch
- `bootstrap_story_gold_set.py`
- `compare_story_thresholds.py`
- `evaluate_story_matching.py`
- `prepare_story_review_batch.py`
- `summarize_story_review_feedback.py`

Pintan a superficie manual poco usada porque:
- no están en Makefile
- no salen en README
- no salen en tests
- aparecen solo en docs de arquitectura/evaluación

Pero borrarlos ahora sería ir de listo sin prueba. Primero hay que decidir si siguen siendo herramientas manuales válidas.

#### Superficie legacy del scheduler
- `scheduler-dry-run`
- `scheduler-once`
- `status`
- `tail-log`
- `scripts/run_scheduled.sh`

Están marcados como legacy, pero siguen siendo ejecutables y siguen documentados. Antes de podarlos hay que comprobar si alguien sigue tirando de eso en cron o en operación manual.

#### Runtime clutter con posible valor operativo
- `.artifacts/`
- `artifacts/`
- `data/`
- `logs/`
- `var/`

Aquí el problema no es “borra todo”, sino que falta política de retención.

### `defer`

#### Frontend navigation/state debt
- `App.tsx` sigue usando query-param mode switching como pseudo-router
- existen dos sistemas URL-state separados (`cluster` y `explorer`)
- esto ya estaba señalado por reviews previas y sigue siendo deuda viva, no código muerto

#### Módulos vivos demasiado gordos
- `src/analysis/pipeline.py` (~2257 LOC)
- `src/semantic/dbstore.py` (~1884 LOC)
- `src/analysis/readside.py` (~1358 LOC)
- `src/semantic/export.py` (~628 LOC)

No toca meterles motosierra en esta iteración. Esto pide lotes medianos y pruebas enfocadas.

## Auditoría de Makefile / tooling

Veredicto:
- el Makefile es **bastante bueno como superficie operativa real**
- la deuda gorda no es que esté roto; es que mezcla targets canónicos con targets legacy y esconde algo del frontend que sí existe

Conclusiones:
- mantener bootstrap/quality/runtime/analysis/semantic/db helpers
- mantener y visibilizar mejor frontend targets
- verificar antes de podar el bloque legacy del scheduler
- alinear docs con la superficie operativa superviviente

## Artefacto principal generado

- `TECH_DEBT_AUDIT.md`

Incluye:
- tabla de findings con IDs
- apéndice de muerto confirmado
- apéndice de sospechosos sin confirmar
- auditoría Makefile/tooling
- lotes futuros acotados (`2A`, `2B`, `2C`, `2D`, `3A`, `3B`, `3C`, `4A`, `4B`)
- orden recomendado de ejecución

## Siguientes lotes recomendados

Orden propuesto:
1. **Lot 2A** — generated/config byproducts + docs leftovers
2. **Lot 2C** — frontend hooks muertos
3. **Lot 2B** — hojas Python muertas
4. **Lot 2D** — higiene de Makefile/help
5. **Lot 4B** — alineación docs/operator contract
6. **Lot 3A / 3B / 3C** — deuda viva en slices acotados
7. **Lot 4A** — limpieza legacy scheduler tras verificación real

## Verificación ejecutada para la auditoría

Inspección realizada con evidencia de wiring/estructura:
- lectura de `Makefile`, `pyproject.toml`, `mkdocs.yml`, `compose.yaml`, configs frontend
- revisión de `src/main.py`, `src/api/app.py`, README y docs índice
- escaneo estructural de imports Python
- escaneo estructural de imports frontend
- comprobación de `git status`, `git ls-files`, `.gitignore`, `frontend/.gitignore`
- revisión de superficie scripts/docs para detectar wiring real vs decorado histórico

## Veredicto honesto

La buena noticia: no hay que hacer una purga épica porque el repo no está lleno de cadáveres por todas partes.

La mala noticia: sí hay bastante deuda de **superficie**, **contrato operativo** y **módulos vivos demasiado gordos**.

La jugada correcta ahora es aburrida y buena:
- borrar lo muerto de verdad
- quitar basura generada que se hace pasar por fuente
- limpiar el contrato Makefile/docs
- y solo después meterse con la deuda viva en lotes pequeños

Eso sí es mantenimiento serio. Lo otro sería teatro de limpieza.