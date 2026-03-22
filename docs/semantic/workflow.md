# Semantic pipeline workflow

## 1) Initialize pgvector-backed schema

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-small'
```

This creates the required tables and can optionally add the ANN index when the underlying script is called with `--ensure-ann-index`.

## 2) Sync embeddings

```bash
export OPENAI_API_KEY='sk-...'
make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
```

What the sync stage actually does:

- loads recent candidate articles from `articles`
- assembles normalized text from source, section, title, summary, and article body
- skips rows whose content hash and embedding model already match the stored embedding record
- upserts embeddings into `article_embeddings`

## 3) Rebuild a projection set

```bash
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

What that stage does:

- loads persisted embeddings
- runs PCA to 2D or 3D based on `projection_set`
- replaces rows in `article_projections` for that set
- recomputes semantic point analysis and semantic cluster summaries for that same set
- optionally writes JSON/HTML outputs if `--out-json` or `--out-html` is provided

## 4) Export offline artifacts

```bash
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

Outputs:

- `data/semantic/articles_embeddings_<stamp>.jsonl`
- `data/semantic/articles_points_<stamp>.json`
- `data/semantic/semantic_analysis_<stamp>.json`
- `data/semantic/semantic_map_<stamp>.html`
- `logs/semantic_<stamp>_metrics.json`

## Date windows

The semantic scripts share one resolution function for date windows. That matters because it keeps sync, project, and export aligned instead of each script inventing its own range semantics.

Supported flags:

- `--days-back N`
- `--date-from YYYY-MM-DD`
- `--date-to YYYY-MM-DD`

## Projection sets

The default projection set is `pca_3d_latest`.

Current code infers projection kind from the set name:

- names starting with `pca_2d` → 2D projection
- names starting with `pca_3d` → 3D projection
- anything else falls back to the default projection kind

That behavior is simple and explicit, but it also means new naming conventions should not be introduced casually.

## Neighbor queries

Use:

```bash
make semantic-neighbors DATABASE_URL=... ARTICLE_ID=123 LIMIT=5
```

The query uses pgvector distance between one seed article and other rows stored with the same embedding model.

## Explorer-facing behavior

The current UI uses persisted `x/y/z` coordinates and reads cluster/outlier annotations from `semantic_point_analysis` and `semantic_clusters`. That part is verified in the backend route and read-side code, not just assumed.
