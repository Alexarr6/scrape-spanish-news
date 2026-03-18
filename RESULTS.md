# RESULTS.md

## Resumen de entrega
La fase siguiente ya no es solo postureo visual del explorer. Ahora el sistema calcula clustering semántico real sobre embeddings, lo persiste por `projection_set`, lo expone por API y lo usa en la UI para filtros y modos visuales sin reventar el alcance.

## Cambios realizados

### Planner
- Reemplacé `PLAN.md` por el plan de la nueva fase centrada en:
  - framing/camera/focus refinado en 2D y 3D
  - clustering semántico sobre embeddings con preferencia por HDBSCAN
  - persistencia y exposición API de clusters
  - visual modes como color-by-source / color-by-cluster
  - mejoras UI acotadas para soportarlo

### Implementer #1 — backend / API
- `src/semantic/analyze.py`
  - Pasé a clustering HDBSCAN sobre embeddings normalizados.
  - Dejé manejo sensato para datasets pequeños.
  - Mantengo análisis por punto con `cluster_id`, `cluster_size`, `is_outlier`, densidad local y diversidad de fuentes cercanas.
- `src/semantic/contracts.py`
  - `ClusterArtifact` ahora incluye `centroid_z`.
- `src/semantic/dbstore.py`
  - Añadí tablas semánticas aditivas para persistir análisis por punto y resúmenes de cluster.
  - `refresh_projection_set()` ahora recalcula y persiste análisis después de regenerar la proyección.
  - `load_explorer_points_page()` y `load_explorer_article_detail()` ya consumen análisis persistido.
  - `cluster_id` y `outlier_only` dejan de ser mentira en los filtros.
- `src/api/contracts/semantic.py`
  - Amplié contratos con `local_density_distance`, `nearby_sources` y `cluster_summaries`.
- `src/api/v1/semantic.py`
  - El meta del explorer ya devuelve resúmenes de cluster.

### Implementer #1 — frontend / explorer
- `frontend/src/lib/types.ts`
  - Nuevos tipos para cluster summaries, color mode y query con cluster/outlier.
- `frontend/src/lib/query.ts`
  - Querystring actualizado con `cluster_id` y `outlier_only`.
- `frontend/src/hooks/useExplorerFilters.ts`
  - Conteo de filtros activos ya contempla cluster y outlier.
- `frontend/src/components/FilterBar.tsx`
  - Añadí selector de cluster y toggle de outliers.
- `frontend/src/components/MapPanel.tsx`
  - Añadí modos visuales `neutral` / `source` / `cluster`.
  - Mejoré reset y focus-selected para 2D y 3D.
  - Los tooltips ya muestran contexto de cluster/outlier.
- `frontend/src/components/StatusBar.tsx`
  - Estado superior ahora refleja modo visual y recuento de clusters.
- `frontend/src/components/InspectorPanel.tsx`
  - El inspector ya muestra densidad local y fuentes cercanas.
- `frontend/src/routes/ExplorerPage.tsx`
  - Estado de `colorMode` integrado en la shell del explorer.

### Architect review
- Dejé revisión directa en:
  - `docs/reviews/ARCH_REVIEW_explorer_clustering_phase_2026-03-18.md`
- Hallazgos principales:
  - la dirección general es correcta
  - quedaban defaults operativos viejos apuntando a `pca_2d_latest`
  - había warning ruidoso de HDBSCAN
  - `load_projected_points()` todavía no hidrataba análisis persistido

### Implementer #2 — follow-up tras architect review
Apliqué solo mejoras inmediatas y de bajo riesgo:
- `src/semantic/analyze.py`
  - Fijé `copy=False` explícitamente en HDBSCAN para quitar el warning futuro.
- `src/semantic/dbstore.py`
  - `load_projected_points()` ahora también hidrata análisis persistido.
- `Makefile`
  - `semantic-project`, `semantic-build` y `semantic-smoke` pasan a usar `pca_3d_latest` por defecto.
- `README.md`
  - Actualicé el copy del explorer y la persistencia semántica.
- `STATUS.md` / `RESULTS.md`
  - Actualizados al estado real de esta fase.

## Verificación ejecutada
```bash
~/.local/bin/uv run pytest -q tests/test_semantic_analysis.py tests/test_semantic_dbstore.py tests/test_api_semantic_explorer.py
```
- Resultado: `23 passed`

```bash
cd frontend && npm run build
```
- Resultado: build OK
- Warnings restantes:
  - warning de chunk grande de Vite
  - warning de `@loaders.gl` / `__vite-browser-external`
  - no rompen el build

## Commits creados
1. `a096336` — `Add persisted HDBSCAN semantic clustering for explorer API`
2. `bdfcd70` — `Add cluster-aware explorer filters visual modes and focus controls`

## Cambios aplicados tras architect review
Pendientes de quedar en commit final de follow-up:
- review markdown en `docs/reviews/ARCH_REVIEW_explorer_clustering_phase_2026-03-18.md`
- defaults 3D en `Makefile`
- hidratación de análisis en `load_projected_points()`
- explicit `copy=False` para HDBSCAN
- docs/estado/resultados actualizados

## Caveats
- No hice smoke manual end-to-end contra Postgres real en esta sesión porque no había un `DATABASE_URL` operativo suministrado para una corrida honesta.
- La experiencia cluster-aware depende de que el projection set haya sido recalculado para persistir análisis:
```bash
make semantic-project PROJECTION_SET=pca_3d_latest DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
```
