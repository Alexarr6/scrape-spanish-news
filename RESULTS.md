# RESULTS.md

## Resumen de entrega
Ya está hecho el arreglo que importaba de verdad: el pipeline semántico en DB ahora acepta ventanas temporales explícitas y el análisis dejó de construir la barbaridad de matriz NxN completa solo para densidad local y fuentes cercanas. En una Raspberry eso no es un detalle; es la diferencia entre funcionar y ponerse a arder con dignidad.

## Cambios realizados

### 1) Contrato temporal reutilizable
Implementé el contrato común pedido en `src/semantic/dbstore.py`:
- `SemanticWindow`
- `resolve_semantic_window(days_back=..., date_from=..., date_to=...)`
- validación centralizada para combinaciones inválidas
- resolución de `--days-back` como ventana inclusiva UTC terminando hoy

Eso evita que cada script rehaga la misma aritmética de fechas de forma cutre.

### 2) Plumbing del window por la ruta DB existente
Apliqué la ventana temporal a la ruta real, sin inventar workarounds paralelos:

- `select_embedding_candidates(...)`
  - filtra por `articles.published_at` cuando se pasa ventana
- `load_embedding_artifacts(...)`
  - filtra embeddings unidos con `articles`
- `refresh_projection_set(...)`
  - acepta `window`
  - en modo acotado borra y reconstruye el `projection_set` solicitado para esa ventana, manteniendo consistencia interna del set
- `load_projected_points(...)`
  - también acepta `window`, para que el build/export no derive en drift absurdo entre embeddings y puntos

### 3) Flags CLI añadidos
Wired end-to-end en:
- `scripts/semantic_sync.py`
- `scripts/semantic_project.py`
- `scripts/build_semantic_map.py`

Flags soportados:
- `--days-back N`
- `--date-from YYYY-MM-DD`
- `--date-to YYYY-MM-DD`

Comportamiento:
- sin flags => historial completo, igual que antes
- `--days-back` no se puede mezclar con fechas explícitas
- `date_from` / `date_to` pueden usarse por separado o juntos

### 4) Optimización de memoria pragmática
En `src/semantic/analyze.py` quité el cuello de botella idiota:
- antes: normalización + matriz completa de distancias NxN
- ahora: normalización + `NearestNeighbors` para obtener vecinos cercanos por fila

Se mantiene:
- clustering HDBSCAN sobre embeddings normalizados

Se calcula ahora vía vecinos cercanos:
- `local_density_distance`
- `nearby_sources`
- `source_neighbor_diversity`

Resultado: semántica prácticamente equivalente para ese contexto, pero sin el pico de memoria más tóxico.

## Tests / cobertura añadida
Añadí y ajusté cobertura para:
- normalización y validación de ventanas temporales
- aplicación de filtros temporales en candidate selection y projected-point SQL
- aceptación de flags temporales en CLI build
- regresión de la ruta nearest-neighbor para análisis

## Verificación ejecutada
```bash
~/.local/bin/uv run pytest -q tests/test_semantic_analysis.py tests/test_semantic_dbstore.py tests/test_semantic_build_cli.py tests/test_api_semantic_explorer.py
```
Resultado:
- `33 passed`

## Commits atómicos creados
1. `047b42f` — `Add temporal window support to semantic sync and projection dbstore flow`
2. `e78f781` — `Reduce semantic analysis memory pressure and add regression coverage`

## Comandos exactos para Raspberry
Flujo con ventana reciente de 2 días:

```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'

make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

Flujo equivalente con fechas explícitas:

```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'

~/.local/bin/uv run python scripts/semantic_sync.py --db-url "$DATABASE_URL" --limit 100 --embedding-model text-embedding-3-small --date-from 2026-03-16 --date-to 2026-03-18
~/.local/bin/uv run python scripts/semantic_project.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --date-from 2026-03-16 --date-to 2026-03-18
~/.local/bin/uv run python scripts/build_semantic_map.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --limit 100 --date-from 2026-03-16 --date-to 2026-03-18
```

Verificación local rápida:

```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
~/.local/bin/uv run pytest -q tests/test_semantic_analysis.py tests/test_semantic_dbstore.py tests/test_semantic_build_cli.py tests/test_api_semantic_explorer.py
```

## Caveats
- No hice smoke end-to-end contra una base Postgres real en esta sesión porque faltaba un `DATABASE_URL` operativo concreto.
- Si reutilizas el mismo `projection_set` en modo bounded y luego quieres volver a historial completo, simplemente vuelve a correr `semantic-project` sin ventana para reconstruir el set completo.
