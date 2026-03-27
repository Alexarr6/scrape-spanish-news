# RESULTS.md — iter/029 analysis pipeline structural refactor phase 2

## Resumen breve

Iter/029 ejecutó la fase 2 del refactor estructural de `src/analysis/pipeline.py` con un corte real y sin tocar la heurística delicada. Se extrajo la generación de candidatos de historia y la carga de vecinos semánticos a `src/analysis/story_candidates.py`, y `ClusterPipeline` quedó como wrapper/orquestador fino para ese subsistema.

## Cambio aplicado

### Nuevo módulo de candidatos
- `src/analysis/story_candidates.py` (nuevo)
  - introduce `StoryCandidateGenerator(session)`
  - mueve sin rediseño funcional:
    - `generate_candidate_pairs()`
    - `load_semantic_neighbor_candidates()`
  - conserva intactas las reglas de:
    - prioridad de orígenes por `recall_mode`
    - límites por origen y por seed
    - carga/filtrado de semantic neighbors
    - `semantic_backfill` en `high_recall`
    - ensamblado de `pair.origins`, `pair.rank` y `CandidateGenerationSummary`
    - degradación segura a `{}` cuando falla el adaptador semántico

### Pipeline conservado como orquestación
- `src/analysis/pipeline.py`
  - mantiene `build_clusters()` sin cambios públicos
  - mantiene `score_pair()` y cierre guardado donde estaban
  - delega `_generate_candidate_pairs()` y `_load_semantic_neighbor_candidates()` al helper extraído
  - conserva los nombres privados viejos como wrappers finos para no romper tests ni callers internos

## Invariantes preservadas

- sin cambios en inclusión/exclusión de candidate pairs
- sin cambios en el orden `default` vs `high_recall`
- sin cambios en límites por origen ni overrides de `high_recall`
- sin cambios en `semantic_backfill_limit`
- sin cambios en fallback de semantic neighbors (`{}`)
- sin cambios en filtrado temporal por `max_days_delta`
- sin cambios en acumulación de `pair.origins`
- sin cambios en semántica de `pair.rank`
- sin cambios en campos/semántica de `CandidateGenerationSummary`
- sin cambios en `build_clusters()` público
- sin cambios en pair scoring, closure o persistencia

## Verificación ejecutada

1. `uv run python -m pytest tests/test_story_candidate_generation.py tests/test_story_clustering.py tests/test_story_matching_eval.py tests/test_story_review.py tests/test_story_pair_scoring.py`

## Resultado de verificación

- suite objetivo: **40 passed**

## Riesgo residual honesto

El refactor quedó donde debía: separar el blob de candidate generation sin fingir que pair scoring también estaba listo para salir. Meter ambas cosas juntas habría sido una idea bastante tonta.