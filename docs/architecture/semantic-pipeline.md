# Architecture: semantic pipeline

## Purpose

The semantic layer exists to answer a different question than story clustering.

Story clustering asks: which articles are likely about the same event?

The semantic explorer asks: how do persisted articles sit relative to each other in embedding space, what neighborhoods do they form, and which points look like outliers?

Those are related, but they are not the same product surface.

## Storage contracts

The semantic database layer in `src/semantic/dbstore.py` owns:

- schema creation and additive migration logic
- embedding model dimension enforcement
- candidate selection and content-hash skipping
- projection rebuilds per `projection_set`
- explorer point, filter, and detail queries
- nearest-neighbor queries

## Embedding candidate assembly

Candidate text is built from normalized source/section context plus title, summary, and article body, then clipped to a maximum character budget.

That matters because the embedding payload is not just raw body text. It deliberately preserves lightweight outlet/section context while still preferring editorial content.

## Projection and analysis

- `src/semantic/project.py` converts embeddings into 2D or 3D PCA coordinates
- `src/semantic/analyze.py` normalizes embeddings, builds a nearest-neighbor graph, computes local density, runs HDBSCAN, and derives cluster summaries

The persisted point analysis then feeds explorer-specific filters such as cluster selection and outlier-only mode.

## Explorer read-side behavior

`load_explorer_points_page()` and related helpers shape the semantic explorer payloads.

They currently provide:

- points with `x/y/z`
- cluster/outlier annotations
- projection bounds
- source/section/cluster filter options
- cluster summaries used by the context rail
- article detail with neighbors

The backend also keeps a lightweight SQLite compatibility branch for published-at formatting in tests, which is a practical detail worth knowing when route tests override dependencies away from Postgres.
