# Semantic pipeline overview

The semantic stack turns persisted article text into embeddings, projections, neighborhood queries, and explorer-facing cluster/outlier metadata.

## Main storage objects

### `article_embeddings`
Stores one embedding row per article.

Key fields:

- `article_id`
- `embedding_model`
- `embedding_dim`
- `embedding` as pgvector
- `content_hash`
- `summary_snippet`

The one-row-per-article uniqueness means a later sync refreshes the record instead of keeping version history.

### `article_projections`
Stores projected coordinates for a named `projection_set`.

Key fields:

- `projection_set`
- `projection_kind`
- `projection_version`
- `x`, `y`, `z`

### `semantic_point_analysis`
Stores explorer-oriented metadata per article and projection set.

Examples:

- cluster id
- cluster size
- outlier flag
- local density distance
- source-neighbor diversity
- nearby source list

### `semantic_clusters`
Stores cluster summaries per projection set for UI filters and context panels.

## Code paths that matter

- `src/semantic/dbstore.py` — schema init, candidate selection, upserts, projection refresh, explorer queries
- `src/semantic/embed.py` — embedding generation
- `src/semantic/project.py` — PCA projection logic
- `src/semantic/analyze.py` — HDBSCAN clustering and neighborhood-derived point analysis
- `src/semantic/export.py` — JSON/HTML artifact writing

## Explorer contract shape

The semantic UI is backed by FastAPI routes under `/api/v1/semantic/explorer`.

Primary endpoints:

- `/points` — paged point payload plus bounds and filter metadata
- `/filters` — filter option payloads
- `/articles/{article_id}` — selected article detail plus neighbors

## Important constraints

- semantic sync requires `OPENAI_API_KEY`
- the embedding model selected during schema init must match the model used during sync
- projection rebuilds are destructive per `projection_set`: existing projections and persisted point-analysis rows for that set are replaced
- the build/export stage reads from persisted embeddings and projections rather than recomputing embeddings itself
