# RESULTS.md — iter/028 analysis pipeline structural refactor phase 1

## Resumen breve

Iter/028 ejecutó la fase 1 del refactor estructural de `src/analysis/pipeline.py` sin tocar heurísticas por accidente. Se extrajo el bloque de **guarded story closure / component assembly / merge decisioning** a `src/analysis/story_closure.py`, y `ClusterPipeline` se quedó como wrapper/orquestador.

## Cambio aplicado

### Nuevo módulo de cierre
- `src/analysis/story_closure.py` (nuevo)
  - introduce `StoryClosureBuilder(high_recall_mode: bool)`
  - mueve sin rediseños el cierre de componentes y sus guardrails:
    - `raw_connected_components()`
    - `build_guarded_components()`
    - `preserve_medium_components()`
    - `merge_supported_components()`
    - `should_merge_components()`
    - `audit_medium_component()`
    - `is_medium_component_edge_compatible()`
    - `classify_closure_edge()`
    - `closure_attach_meta()`
    - `should_attach_candidate()`

### Pipeline conservado como orquestación
- `src/analysis/pipeline.py`
  - mantiene `build_clusters()` sin cambios públicos
  - mantiene `score_pair()` y candidate generation en sitio
  - inyecta `high_recall_mode` explícitamente al builder
  - conserva los nombres privados viejos como wrappers finos para no romper tests ni callers internos que los inspeccionan/monkeypatchean

## Invariantes preservadas

- sin cambios en heurísticas de clustering
- sin cambios en `score_pair()`
- sin cambios en candidate generation
- sin cambios en persistencia o payloads de membership reason
- sin cambios en `ClusterPipeline.build_clusters()`
- sin deriva en métricas/contratos
- sin deriva en comportamiento `high_recall_mode`

## Verificación ejecutada

1. `uv run python -m pytest tests/test_story_clustering.py tests/test_story_pair_scoring.py tests/test_story_candidate_generation.py tests/test_story_matching_eval.py tests/test_story_review.py`

## Resultado de verificación

- suite objetivo: **40 passed**

## Riesgo residual honesto

El diff es deliberadamente aburrido: extracción mecánica y wrappers. Perfecto. Si esto se ponía creativo, era señal de que el scope se estaba yendo al carajo.