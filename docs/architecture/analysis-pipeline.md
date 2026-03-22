# Architecture: analysis pipeline

## Purpose

The analysis pipeline converts persisted article rows into richer editorial structure: article type, tags, entities, key phrases, claims, and same-story clusters.

## Main code paths

- `src/analysis/heuristics.py` — heuristic article typing, tag inference, candidate entities, title similarity
- `src/analysis/canonicalization.py` — canonical entity naming and alias normalization rules
- `src/analysis/pipeline.py` — enrichment pipeline plus cluster rebuild pipeline
- `src/analysis/readside.py` — API-facing cluster list/detail/filter payload assembly

## Enrichment flow

`AnalysisPipeline.enrich_articles()` currently:

1. seeds canonical tags if needed
2. loads recent articles within a date window
3. skips articles whose content hash has not changed
4. starts with heuristic enrichment
5. optionally upgrades with OpenRouter output when that client is configured and returns valid schema-conforming data
6. persists article analysis, article tags, entity aliases, and entity mentions

That design keeps the heuristic path as the boring fallback instead of making the whole pipeline hostage to an external model call.

## Clustering flow

`ClusterPipeline.build_clusters()` currently:

1. loads recent enriched articles
2. compares candidate pairs within a bounded publication-distance window
3. computes a weighted story similarity score
4. rejects pairs via hard blocks or threshold failure
5. converts accepted edges into connected components
6. rewrites persisted story-cluster, member, and cluster-entity tables

## Pair scoring

The score is a weighted mix of:

- semantic/key-phrase overlap
- title similarity
- shared entity overlap
- tag overlap
- key-phrase overlap
- temporal proximity

The implementation also applies penalties for analysis/follow-up cases and uses a hard block for some opinion/editorial combinations. Those are product rules, not generic clustering math, so they deserve explicit docs and docstrings.

## Read-side payload assembly

The cluster API is not a thin ORM dump.

`src/analysis/readside.py` composes:

- cluster cards with primary-tag and top-entity summaries
- cluster detail payloads with member tags and entity snippets
- filter metadata based on the currently matched cluster set

That read-side separation is useful because UI-facing payload shape and persistence shape are not the same thing.
