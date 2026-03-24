# Explorer editorial lenses — architecture handoff (2026-03-24)

## Verdict

Do **not** turn Explorer into a giant editorial control matrix.

The repo already has a solid Phase 1 visual grammar:
- `sem_mode=highlight|filter`
- `sem_color=neutral|source|cluster|active-match`
- active-match emphasis in `MapPanel`
- Stories → Explorer defaults to highlight-in-context
- article detail rail already shows full editorial analysis

What is missing is not another pile of controls. What is missing is a clean, point-level editorial contract so the map can do something honest.

The right first slice is:
- **one editorial dimension at a time**
- **article type first**
- usable across:
  - highlight
  - filter
  - color-by-dimension

Bias and tone are real later candidates, but shipping them in the first Explorer lens pass would be premature bullshit.

---

## What I inspected

Planning / prior architecture:
- `PROJECT_BRIEF.md`
- `TASK_CONTRACT.md`
- `PLAN.md`
- `logs/iterations/008.md`
- `docs/architecture/2026-03-24-explorer-visual-modes-frontend-architecture.md`

Backend / API:
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- `src/api/contracts/clusters.py`
- `src/api/contracts/editorial.py`
- `src/analysis/readside.py`

Frontend:
- `frontend/src/lib/types.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`

Tests:
- `tests/test_api_semantic_explorer.py`

---

## Repo truth right now

### Already real
- Explorer visual mode is already a first-class concept.
- Color mode is already URL-backed.
- `MapPanel` already knows how to differentiate:
  - selected
  - neighbors
  - hovered
  - active-match
  - receding non-match
- `ExplorerContextRail` already explains highlight vs filter.
- Stories and article detail already expose editorial analysis on non-map surfaces.

### Still missing
- `ExplorerPoint` has **no editorial preview**.
- Explorer `/filters` metadata has **no editorial options / counts**.
- Explorer `/points` query contract has **no editorial target params**.
- There is **no legend semantics** for editorial missing-data states on the map.

That means the map cannot honestly do article type / bias / tone lensing yet, even though the repo does have editorial data elsewhere.

---

## First-slice architecture

## 1. One editorial lens target at a time

First cut gets exactly one active editorial lens target.

```ts
type ExplorerEditorialDimension = 'article_type'

type ExplorerEditorialTarget = {
  dimension: 'article_type'
  value: string
} | null
```

Do not allow:
- article type + bias target together
- article type + tone target together
- AND/OR editorial builders
- dual highlight overlays

That would instantly turn the Explorer controls into mud.

### Why one target is the right cut
- matches the current Phase 1 active-match grammar
- keeps the legend understandable
- avoids compound-state lies
- gives backend a tiny contract instead of a swamp

---

## 2. Lock the interaction model: article type first

### Control structure
Keep the current top-level structure intact:
- View mode (`2D | 3D`)
- Visual mode (`Highlight | Filter`)
- Color by (`Neutral | Source | Cluster | Active match | Article type`)

Add one new bounded control group:
- `Editorial lens`
  - dimension: fixed to `Article type` in v1
  - value: one article-type value
  - clear action

### Interaction rules

#### A. No editorial target selected
- existing Explorer behavior stays exactly as-is
- `sem_color=article-type` is still allowed if backend point preview exists
- this is distribution view, not active-match view

#### B. Editorial target selected + `sem_mode=highlight`
Meaning:
- keep the current dataset visible
- emphasize points whose `article_type` matches the selected value
- recede non-matches
- keep unknown/pending/failed visible as neutral context

#### C. Editorial target selected + `sem_mode=filter`
Meaning:
- narrow server-side to matching points only
- selected article / hovered / neighbors should not resurrect non-matching hidden points
- this is a subset view, not a context view

#### D. `sem_color=article-type`
Meaning:
- color all currently visible points by article type
- works with or without an editorial target
- if an editorial target is also selected, target matching still comes from `sem_mode`, not color

### Product wording
Use **Article type** as the user-facing label.
Not “editorial class,” not “content framing class,” not other overcooked nonsense.

---

## 3. Exact URL/state semantics

Keep the current params. Add bounded editorial params.

### Existing params kept
- `sem_mode=highlight|filter`
- `sem_color=neutral|source|cluster|active-match|article-type`
- existing query params (`sem_search`, `sem_source`, `sem_section`, `sem_cluster`, `sem_story_cluster`, `sem_from`, `sem_to`, `sem_outliers`, `sem_limit`, `sem_article`)

### New params
- `sem_editorial_dim=article_type`
- `sem_editorial_value=<label>`

### Required rules

#### URL validity
- if `sem_editorial_value` is present and `sem_editorial_dim` is missing, frontend should drop the orphaned value
- if `sem_editorial_dim` is unknown, frontend should clear both editorial params
- if `sem_editorial_dim=article_type` and value is unknown to the current enum set, frontend may preserve it in URL but should show it as an active raw value until cleared

#### Effective semantics
- `sem_editorial_dim + sem_editorial_value` define the active editorial target
- `sem_mode` defines whether that target is:
  - contextual highlight
  - or hard filter
- `sem_color` defines point coloring independently

### First-slice default behavior
Do **not** set editorial params by default when opening Explorer.

Stories → Explorer remains:
- `sem_story_cluster=<id>`
- `sem_mode=highlight`
- `sem_color=active-match`

Editorial lenses are user-selected analysis tools, not default route state.

### Combination precedence
For active-match emphasis in the first slice:
1. editorial target, if present
2. otherwise existing Phase 1 target precedence:
   - story cluster
   - semantic cluster
   - search
   - source

This matters.
If article type is actively selected, that becomes the active lens target. The old seed target can still exist in URL, but it should not compete visually for the same “match” channel.

That is the cleanest rule and the least confusing one.

---

## 4. Exact backend contract required

## A. Add editorial preview to `ExplorerPoint`

This is mandatory.

Add a lightweight point-level editorial preview instead of dumping full `ExplorerEditorialSummary` onto every point.

### Contract
In `src/api/contracts/semantic.py`, add something like:

```py
class ExplorerPointEditorialReviewFlags(BaseModel):
    low_confidence: bool = False
    needs_review: bool = False
    failed_analysis: bool = False
    pending_analysis: bool = False
    out_of_domain: bool = False


class ExplorerPointEditorialPreview(BaseModel):
    analysis_status: str = 'pending'
    editorial_applicability: str = 'full'
    article_type: str = 'unclear'
    article_type_confidence: float = 0.0
    bias_label: str = 'unclear'
    bias_confidence: float = 0.0
    tone_emotional: str = 'unclear'
    review_flags: ExplorerPointEditorialReviewFlags = Field(default_factory=ExplorerPointEditorialReviewFlags)


class ExplorerPoint(BaseModel):
    ...
    analysis: ExplorerSemanticSummary = Field(default_factory=ExplorerSemanticSummary)
    editorial_preview: ExplorerPointEditorialPreview | None = None
```

### Why this exact shape
Because it covers:
- article type now
- bias next
- tone after that
- pending / failed / out_of_domain treatment from day one

Without forcing the frontend to fetch full article detail just to color dots.

## B. Populate preview from existing read-side logic

The repo already has product-grade shaping logic in `src/analysis/readside.py`:
- `_shape_product_editorial_summary()`
- `_shape_member_editorial_preview()`

Do **not** invent a second contradictory editorial semantics path.

Best move:
- add a dedicated explorer preview shaper that reuses the same source semantics
- or reuse a narrowed variant of `_shape_product_editorial_summary()`

### Mandatory preview semantics
If no editorial row exists:
- `analysis_status = pending`
- `article_type = unclear`
- `editorial_applicability = full`
- `review_flags.pending_analysis = true`

If analysis failed:
- `analysis_status = failed`
- keep `article_type = unclear`
- `review_flags.failed_analysis = true`

If applicability is `limited` or `out_of_domain`:
- preserve it exactly
- do not silently coerce it to unknown

## C. Add editorial query params to `/api/v1/semantic/explorer/points`

Mandatory for real filter mode.

### Query params
- `sem_editorial_dim` (first cut only accept `article_type`)
- `sem_editorial_value`

### Backend behavior
If `sem_editorial_dim=article_type` and `sem_editorial_value` present:
- `sem_mode=filter`:
  - narrow SQL result set to `article_editorial_analysis.article_type = :value`
  - probably left join / inner join editorial analysis depending on query shape
  - pending/unknown rows are excluded unless value explicitly equals `unclear` later
- `sem_mode=highlight`:
  - do **not** filter the base dataset
  - include `editorial_preview` for every returned point
  - frontend computes match state

This mirrors the existing highlight/filter split already used for story cluster and search. Good. Reuse it.

## D. Add editorial metadata to Explorer filters/meta

This is strongly recommended and should be treated as part of the same slice, because hardcoded option lists are weak.

### Add to `ExplorerFiltersResponse`
Something like:

```py
class ExplorerEditorialOption(BaseModel):
    value: str
    count: int = 0

class ExplorerEditorialFilterMetadata(BaseModel):
    article_type: list[ExplorerEditorialOption] = Field(default_factory=list)
    coverage: dict[str, int] = Field(default_factory=dict)
```

Then:

```py
class ExplorerFiltersResponse(BaseModel):
    ...
    editorial: ExplorerEditorialFilterMetadata | None = None
```

### Minimum required counts
For the current scoped dataset or projection set filters endpoint, expose counts for:
- article type values
- `unknown`
- `pending`
- `failed`
- `limited`
- `out_of_domain`

This is not decorative. The legend and control labels need it.

If you skip counts entirely, the frontend can still ship, but it will be a weaker product slice.

---

## 5. Legend semantics and missing-data treatment

This part cannot be hand-wavy. The repo already has real editorial states. Respect them.

## Article-type color legend

### Normal article-type categories
Color these with categorical hues:
- `news`
- `opinion`
- `editorial`
- `analysis`
- `interview`
- `review`
- `feature`
- `live`
- `unclear`

Use stable colors. Do not randomize. Do not merge `unclear` into a normal category.

### Missing-data / quality states
These should **not** pretend to be article types.

#### `unknown`
Definition for Explorer map purposes:
- analysis exists or preview exists, but effective dimension value is `unclear`

Treatment:
- muted gray
- visible in color-by mode
- included as `Unknown` legend row
- does **not** count as a match unless user explicitly targets `unclear` later

#### `pending`
Definition:
- no analysis row yet / `analysis_status = pending`

Treatment:
- muted dashed/low-emphasis gray in legend copy
- on map: same neutral family as unknown, but distinguishable in legend and hover text
- never treated as a positive match in highlight mode
- excluded from filter mode unless future support adds `value=pending`

#### `failed`
Definition:
- `analysis_status = failed`

Treatment:
- muted warning-neutral color, not bright red drama
- separate legend row from pending
- never treated as a match
- excluded from filter mode unless future explicit diagnostic filtering is added

#### `limited`
Definition:
- `editorial_applicability = limited`

Treatment:
- still show actual article type if present
- but mark legend/hover/copy as limited-scope
- in color-by mode, keep the base article-type hue and apply reduced alpha or badge/tooltip caveat
- do **not** remap limited into unknown; that would throw away usable signal

#### `out_of_domain`
Definition:
- `editorial_applicability = out_of_domain`

Treatment:
- if article type is effectively unclear, render with muted out-of-domain neutral
- if future dimensions rely on applicability more strictly, this state becomes more important for bias/tone
- for article type v1, out_of_domain is mostly a caveat state, not the primary grouping key

### Summary rule
For **article type**:
- pending / failed / unknown are non-match neutral states
- limited keeps its article-type label but with caveat
- out_of_domain is shown honestly and muted when it destroys interpretability

That is the cleanest compromise.

---

## 6. Allowed now vs deferred

## Allowed now

### A. Editorial target + highlight
Allowed:
- `sem_editorial_dim=article_type`
- `sem_editorial_value=opinion`
- `sem_mode=highlight`
- color can be:
  - `neutral`
  - `source`
  - `cluster`
  - `active-match`
  - `article-type`

### B. Editorial target + filter
Allowed:
- same target params
- `sem_mode=filter`
- color can still be any of the above, including `article-type`

### C. Article-type color without active target
Allowed:
- `sem_color=article-type`
- no editorial target

This is useful for distribution scanning.

### D. Existing non-editorial filters remain usable
Allowed together with article type lens:
- date window
- section
- source subset
- point limit
- outlier toggle

Those are normal dataset-scope controls.

---

## Deferred

### A. Multiple editorial dimensions at once
Defer:
- article type + bias
- article type + tone
- bias + tone

### B. Tone as a generic label
Defer generic `tone`.
When tone lands, it should be explicitly `tone_emotional`, because the repo already distinguishes:
- `tone_emotional`
- `tone_target`

Anything else is muddy labeling.

### C. Bias as first Explorer lens
Defer bias until after article type proves the UI grammar.
Bias needs stronger legend and confidence treatment.

### D. Dual active-match overlays
Defer competing match channels like:
- story cluster active-match + article type active-match at same time
- search active-match + article type active-match at same time

In first cut, editorial target wins the active-match channel if present.

### E. Filtering diagnostic states directly
Defer explicit values like:
- `pending`
- `failed`
- `limited`
- `out_of_domain`

Expose them in legend/meta first. Add direct filtering later if users actually need diagnostic slicing.

### F. Full editorial-dimension abstraction in UI
Defer generic “dimension picker” until at least article type is real and one more dimension is proven.
For now, a hardcoded `Article type` lens control is cleaner.

---

## 7. Repo-specific frontend implications

### `frontend/src/lib/types.ts`
Add:
- `ExplorerPointEditorialPreview`
- `ExplorerEditorialDimension = 'article_type'`
- `ExplorerColorMode` extension with `'article-type'`
- editorial filter metadata types

### `frontend/src/hooks/useExplorerUrlState.ts`
Add URL support for:
- `sem_editorial_dim`
- `sem_editorial_value`
- parse/serialize `article-type` color mode

### `frontend/src/routes/ExplorerPage.tsx`
Derive:
- `activeEditorialTarget`
- effective active-match precedence where editorial target wins

### `frontend/src/components/explorer/ExplorerControlBar.tsx`
Add bounded `Editorial lens` controls.
Do not mix them into the existing `Refine` drawer only. The lens is a first-class visual analysis control.

### `frontend/src/components/explorer/MapPanel.tsx`
Extend:
- point match logic for `article_type`
- color logic for `article-type`
- keep selection / neighbors / hovered above lens styling

### `frontend/src/components/explorer/ExplorerContextRail.tsx`
Add:
- article-type legend rows
- honest missing-data copy
- mode-aware language:
  - highlighted in context
  - filtered to matching article type

---

## 8. Recommended exact implementation scope for the next agent

## Next agent
**Backend/data implementer** if you want to start landing code immediately.

The architecture is locked tightly enough now.

If the project flow insists on one more approval gate, use **frontend implementer after backend**. But the actual blocker is backend contract, not more philosophy.

## Exact implementation scope

### Backend
Touch only what is needed:
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- maybe a tiny helper in `src/analysis/readside.py`
- tests covering:
  - point preview payload
  - article-type filter mode behavior
  - highlight mode preserves broad dataset while including preview
  - filters/meta includes article-type options and coverage counts if implemented

### Frontend after backend
- add `Article type` lens controls
- add `article-type` color mode
- wire URL state
- wire active-match precedence
- add legend / missing-data semantics
- do **not** add bias or tone in the same pass

---

## Bottom line

The clean first slice is brutally simple:
- one editorial dimension
- article type only
- one active target at a time
- highlight/filter/color all supported
- honest missing-data semantics
- tiny point preview contract

Anything wider than that in this iteration is how you turn a good Explorer into a clown car.