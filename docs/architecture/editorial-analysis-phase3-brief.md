# Editorial Analysis — Phase 3 Brief

Status: preserved future brief for planner / architect / implementer

## Why this exists

Phase 1 and Phase 2 established the foundation for article-level editorial analysis:
- dedicated persistence
- strict contracts and validation
- dedicated OpenRouter prompt path
- separate editorial analysis pipeline
- article-level detail endpoint
- list/filter read API
- operational controls for pending/failed/targeted runs
- review-friendly inspection flags

This file exists so future planning does not lose the product intent and accidentally jump into the wrong thing.

## What Phase 3 is for

Phase 3 is where editorial analysis becomes a **comparison product**, not just a per-article annotation system.

The goal is to move from:
- “what is the bias/tone of this article?”

to:
- “how do different media frame the same story?”
- “how ideologically dispersed is coverage of this event?”
- “which outlets use different tones, frames, or emphasis on the same cluster?”

## Prerequisite before Phase 3

Do **not** begin Phase 3 blindly.

Before starting, confirm at least one controlled manual review batch has happened and that editorial analysis v1 is not obviously unreliable.

Minimum confidence gate:
- article-level outputs are structurally stable
- evidence spans are mostly useful
- confidence is not wildly inflated
- weak-signal pieces are not over-labeled ideologically
- review flags are catching suspicious cases reasonably well

If that gate is not met, do prompt/schema calibration first.

## Phase 3 objectives

### 1. Cluster-level editorial aggregation
Add read-side aggregation for story clusters so we can answer:
- average / median `bias_score` within a cluster
- distribution of `bias_label` across cluster articles
- dominant tone dimensions per outlet inside the cluster
- ideological spread / dispersion of the cluster
- percentage of low-confidence or unclear outputs inside a cluster

This should stay on the **read side first**.
Do not rush into heavy new write models unless clearly necessary.

### 2. Same-story multi-outlet comparison
For one cluster/story, expose comparison views across outlets.

Desired comparison dimensions:
- ideological direction per article/outlet
- emotional tone differences
- opinionatedness differences
- sensationalism differences
- framing device differences
- confidence and review flags

This is one of the main product-value surfaces.

### 3. Framing divergence / convergence
Go beyond raw label comparison.
We want to see:
- which frames are shared across outlets
- which frames are emphasized by some outlets but not others
- whether disagreement is ideological, tonal, or both

This is where the system starts becoming analytically interesting instead of just decorative.

### 4. Cluster-level reviewability
Any aggregate surface must still be inspectable.

Need the ability to drill down from cluster summary to:
- individual article results
- rationale
- evidence spans
- review flags

No black-box cluster score bullshit.

## Recommended Phase 3 scope

### In scope
- cluster-level read-side aggregation endpoints
- story-level comparison endpoint(s)
- outlet comparison payloads over a cluster
- review-first summary fields (counts, spread, uncertainty)
- minimal backend shaping needed for those reads

### Out of scope unless explicitly approved
- large frontend redesign
- permanent outlet ideology scoring as a “truth” system
- automated public claims about media bias quality
- heavy normalization layers unless the read-side clearly demands them
- article_type unification refactor with old `article_analysis`

## Recommended backend route

### Step A — add cluster editorial read models / queries
Build read-side queries joining:
- `story_clusters`
- `cluster_members`
- `articles`
- `article_editorial_analysis`

Focus on cluster summaries and cluster member comparison rows.

### Step B — add story comparison endpoints
Possible endpoints:
- `GET /api/v1/editorial-analysis/clusters/{cluster_id}`
- `GET /api/v1/editorial-analysis/clusters/{cluster_id}/compare`
- `GET /api/v1/editorial-analysis/clusters/{cluster_id}/outlets`

These should return:
- aggregate cluster metrics
- per-article or per-outlet comparison rows
- uncertainty/review info

### Step C — add divergence metrics
Recommended metrics:
- `bias_score_mean`
- `bias_score_stddev` or range
- count by `bias_label`
- count by `tone_emotional`
- count by `opinionatedness`
- shared vs unique `framing_devices`
- `% unclear_bias`
- `% low_confidence`

Keep it readable. Fancy math is optional; clarity is mandatory.

## Product guidance

### What the product should say
The product should help the user understand:
- how the same event is narrated differently
- whether divergence is mostly ideological, tonal, or frame-based
- where confidence is weak and review is needed

### What the product should NOT pretend
It should **not** pretend to produce final objective truth about media ideology.
It should present:
- model outputs
- evidence spans
- uncertainty
- comparison structure

This is analysis support, not holy scripture.

## Phase 3 review principles

Every cluster-level claim should be traceable back to article-level evidence.
If an aggregate says:
- cluster leans center-right
- outlet A is more inflammatory
- outlet B uses humanitarian framing more often

then the user must be able to inspect the underlying article rows.

## Design cautions

### 1. Do not over-aggregate too early
Averages can hide disagreement and noise.
Always preserve distribution and drilldown.

### 2. Do not create fake outlet ideology truth tables yet
This system is about article and story framing first.
Permanent outlet ranking is a later, riskier layer.

### 3. Respect low-confidence data
Cluster summaries must visibly account for uncertainty.
If most articles are `unclear`, the cluster summary should say so instead of bluffing.

### 4. Avoid article-type refactor creep
Current clustering still depends on existing `article_analysis.article_type` flows.
Do not smuggle that refactor into Phase 3 unless separately planned.

## Suggested validation for Phase 3

Before calling it done, validate on real clusters:
- choose 3 to 5 clusters with multi-outlet coverage
- inspect per-article results first
- then inspect aggregate output
- confirm the aggregate reflects the underlying items rather than hallucinating coherence

Questions to ask:
- Does the cluster summary match the article-level evidence?
- Are disagreement and uncertainty visible enough?
- Does the comparison surface help a human understand framing differences quickly?
- Are there clusters where the system clearly overstates certainty?

## Suggested execution slices

1. read-side queries for cluster/article joins
2. cluster summary endpoint
3. cluster comparison endpoint
4. uncertainty/spread metrics
5. docs/status/results update
6. optional frontend consumption later

## Phase 3 success condition

Phase 3 is successful if the repo can answer this cleanly:

> For one story cluster, show how different outlets framed it ideologically and tonally, with uncertainty and evidence visible.

If it cannot do that, it is not Phase 3 yet — it is just extra plumbing.
