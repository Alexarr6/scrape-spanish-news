# RESULTS.md — iter/027 semantic layer structural refactor phase 1

## Resumen breve

Iter/027 ejecutó la fase 1 del refactor estructural de la capa semántica sin montar un circo innecesario.

Se extrajo el **explorer read-model shaping** y los **helpers de metadata editorial/cluster/filtros** desde `src/semantic/dbstore.py` a un módulo dedicado: `src/semantic/explorer_readside.py`. `dbstore.py` se quedó con lo que debía: esquema, persistencia, orquestación SQL y loaders públicos.

`src/semantic/export.py` se inspeccionó y se dejó quieto a propósito. Tocar eso ahora habría sido ensanchar el diff por puro deporte.

## Cambio aplicado

### Nuevo módulo read-side
- `src/semantic/explorer_readside.py` (nuevo)
  - mueve el shaping de `editorial_preview`
  - mueve el shaping de `PointAnalysisArtifact` para filas del explorer
  - mueve parseo JSON defensivo de campos editoriales/read-model
  - mueve helpers de metadata para:
    - bounds de proyección
    - valores distintos / filtrados
    - clusters disponibles
    - resúmenes de cluster
    - metadata editorial de explorer

### Orquestación conservada en dbstore
- `src/semantic/dbstore.py`
  - mantiene schema/init helpers
  - mantiene upserts/persistencia de embeddings y projections
  - mantiene query orchestration y SQL de los loaders públicos
  - mantiene entrypoints públicos:
    - `load_projected_points()`
    - `load_explorer_points_page()`
    - `load_explorer_filter_options()`
    - `load_explorer_article_detail()`
  - ahora delega el shaping read-side al nuevo módulo

## Invariantes preservadas

- sin cambios en schema
- sin cambios en contratos API/router
- sin cambios en export HTML
- sin cambios en nombres ni firmas de loaders públicos
- se preservó el payload del explorer, incluyendo:
  - `editorial_preview`
  - `analysis.cluster_id`
  - `analysis.story_cluster_ids`
  - metadata de filtros/editorial
  - cluster summaries

## Verificación ejecutada

1. `uv run python -m pytest tests/test_semantic_dbstore.py tests/test_api_semantic_explorer.py tests/test_semantic_export.py tests/test_semantic_build_cli.py`

## Resultado de verificación

- suite objetivo: **60 passed**

## Commits

- `refactor(semantic): extract explorer readside helpers`

## Riesgo residual honesto

Sí, `dbstore.py` sigue siendo grande. Pero ya perdió un bloque de responsabilidad real y bien delimitado. Eso era la misión. Convertir esta iteración en un “ya que estamos” sobre `export.py` habría sido una cagada de scope.