# iter/008 review — Explorer article-type lens (2026-03-24)

## Verdict

**Approve with caveats.**

This is a real product slice, not decorative glitter. The core interaction model holds up, the map semantics are mostly honest, and article type is the right first editorial lens.

But don’t oversell it. Two caveats matter:
1. the backend/frontend contract is only **partially** future-ready for bias/tone
2. the missing-data story is decent, but not fully consistent between color semantics and legend semantics

---

## Files inspected

Planning / prior direction:
- `PROJECT_BRIEF.md`
- `TASK_CONTRACT.md`
- `PLAN.md`
- `logs/iterations/008.md`
- `docs/architecture/2026-03-24-explorer-editorial-lenses-architecture.md`
- `STATUS.md`
- `RESULTS.md`

Backend / contracts / tests:
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`

Frontend:
- `frontend/src/lib/types.ts`
- `frontend/src/lib/explorerEditorial.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`
- `frontend/src/routes/ExplorerPage.tsx`

---

## 1) Interaction model coherence

### Verdict
**Coherent enough to ship.**

The key win is that the slice did not invent a second grammar. It extends the existing Explorer visual grammar instead of fighting it:
- `sem_mode=highlight|filter` still means what it said before
- article type becomes just another active match target
- editorial target takes active-match precedence when present
- selected / hovered / neighbor states still outrank lens styling

That last part matters. If selection and neighborhood had lost priority, the whole map would have turned into an unreadable fight between local focus and global lensing. It didn’t.

### What works well
- `ExplorerPage.tsx` makes editorial target first in active-match precedence. That is the right call.
- `MapPanel.tsx` uses the same match machinery for editorial target as it already used for story/search/source. Good. Reuse beats cleverness.
- `ExplorerContextRail.tsx` explains highlight vs filter in plain terms instead of pretending users will infer it from colors alone.
- The control bar keeps article type as one bounded lens, not a dropdown swamp.

### What still feels a bit rough
- `Editorial lens` is first-class in the bar, but `Color by` includes `Article type` even with no active target. That is fine analytically, but it creates a mild mental split: one control chooses a target, the other chooses a distribution view. It works, but only because the rail copy does a lot of cleanup.
- The badge just says `Article type lens`. It could be more specific about the active value, because right now the user has to parse the select to know the actual target.

This is not broken. It’s just a little drier than it should be.

---

## 2) Highlight vs filter vs color-by honesty

### Verdict
**Mostly honest. Not perfect, but good enough.**

The implementation mostly keeps the semantics straight:
- **highlight** = full cloud remains visible, matches pulled forward
- **filter** = backend subset only
- **color-by article type** = categorical distribution of visible points

That is the correct product grammar.

### Evidence from landed code
- Backend only applies article-type narrowing in `_build_explorer_where_clause()` when `visual_mode == "filter"`.
- Highlight mode keeps the broader dataset and sends point previews so the frontend can emphasize matches locally.
- `MapPanel.tsx` recedes non-matches in highlight mode instead of deleting them.
- `ExplorerContextRail.tsx` explicitly says when Explorer is narrowed vs when context remains visible.

### Caveat
The semantics are clean in logic, but slightly muddier in the legend:
- `colorMode === 'article-type'` shows article types and also separate diagnostic rows for unknown/pending/failed/limited/out_of_domain.
- But `limited` is not actually a separate color bucket in the map. The code keeps the article-type hue and only talks about limited as a caveat state.

So the legend is a bit more categorical than the rendering really is. That is survivable, but it’s not perfectly honest.

Also: `articleTypeColorRgb()` only keys off `article_type`. It does not visually distinguish `limited`, `pending`, `failed`, or `out_of_domain` on-point in color mode. The tooltip and legend carry the nuance, but the mark itself does not. That is a product compromise, not a lie, but call it what it is.

---

## 3) Is article-type lensing genuinely useful?

### Verdict
**Yes. It earns its keep.**

This is not decorative.

Article type is the least bullshit editorial lens to start with because it answers a real map question:
- are semantic neighborhoods mixing reporting, opinion, and analysis?
- does a story cluster contain genre separation by source?
- when a cloud looks coherent semantically, is it actually heterogeneous in editorial form?

That is useful in this repo because the whole product is trying to compare semantic proximity with editorial framing. Starting with article type is sober and smart.

### Why it works here specifically
- The Explorer is already a semantic neighborhood tool, so article type adds an interpretable overlay.
- Stories and article detail already established editorial framing elsewhere, so this does not come out of nowhere.
- Article type in highlight mode is especially useful: it lets you inspect whether one semantic patch is mostly straight reporting or contains a pocket of opinion/editorial pieces without destroying context.

### What stops it from being great yet
- There is no stronger summary of *why* the current article-type distribution matters in the current subset. You get dots, legend, and rail copy, but not much analytical lift beyond that.
- Metadata counts are useful, but the experience is still basically “pick a category and squint at the cloud.” That’s acceptable for v1, but it is where the next bounded improvement should focus.

Still: useful, not decorative. That box is checked.

---

## 4) Missing-data states

### Verdict
**Handled competently, but with one important mismatch.**

The good part:
- backend distinguishes pending / failed / unclear / limited / out_of_domain in the preview and coverage metadata
- frontend refuses to treat pending/failed as positive matches
- tooltips and rail text stay sober
- filter mode excludes pending/unknown unless a real matching article type exists

That is the right baseline.

### The mismatch
The implementation treats missing-data states more honestly in **copy** than in **visual encoding**.

Examples:
- `describeEditorialPreview()` is careful and explicit.
- `getEditorialStatusBucket()` has a sensible precedence order.
- But `colorForPoint(..., 'article-type')` colors by article type only, so pending/failed/out_of_domain do not actually get their own mark encoding on the map.

That means the legend implies more visual separation than the map actually provides.

### Another caveat
Coverage labeling in `DatasetSummary` says:
- `Editorial coverage · X analyzed / visible points, Y pending, Z failed.`

But `coverage.total` is actually total visible points, not analyzed points. That sentence is sloppy. It reads as if all total points are analyzed, which is false whenever pending exists. That copy should be fixed before anyone starts bragging about analytical honesty.

### Net
The state handling is decent. The wording and legend need tightening.

---

## 5) Contract cleanliness for later bias/tone extension

### Verdict
**Decent foundation, but not as clean as it should be.**

This is the biggest caveat in the slice.

### What is good
- URL grammar is clean: `sem_editorial_dim` + `sem_editorial_value`
- one active editorial target is a sane base for later extension
- point-level `editorial_preview` is absolutely the right structural move
- metadata block under `meta.editorial` is the right place for lens options / counts

### What is not clean enough yet
#### A. Backend shaper is already smuggling future fields, but the contract does not declare them
`_editorial_preview_for_row()` returns:
- `bias_label`
- `bias_confidence`
- `tone_emotional`

But `ExplorerPointEditorialPreview` in `src/api/contracts/semantic.py` only declares:
- `analysis_status`
- `editorial_applicability`
- `article_type`
- `article_type_confidence`
- `review_flags`

Because Pydantic ignores extra fields by default, those future-looking fields are just dropped on the floor at the API contract layer. So the shaping code is future-leaning, but the contract is not.

That is not harmful today, but it’s untidy. It creates the illusion of extensibility without actually providing it.

#### B. `ExplorerEditorialDimension` on the frontend is hardcoded to `'article_type'`
That is correct for this slice, but it means future bias/tone extension is not just a backend add. The UI, types, legends, and color semantics will all need another structural pass.

#### C. Metadata is article-type specific, not truly editorial-generic
`ExplorerEditorialMetadata` currently exposes only `article_type` options plus generic coverage counts. That is fine for the slice, but it is not a generalized lens metadata contract yet.

### Bottom line
The contract is good enough to extend, but not “plug bias/tone in next week and go home” clean. It needs one cleanup pass before adding another editorial dimension.

---

## 6) What should improve next

## Next bounded recommendation
**Do one contract-tightening + legend-honesty pass before adding bias.**

That means:
1. tighten the `editorial_preview` contract so it either
   - only contains fields the API truly promises, or
   - explicitly declares the next-ready fields it intends to expose
2. fix dataset/legend copy so coverage language is accurate
3. make missing/diagnostic state semantics visually and textually consistent in article-type color mode
4. keep the one-lens model intact

This is the right next move because the current slice is good enough to justify hardening, but not clean enough to safely multiply.

### Why this should be next
Because the dangerous temptation now is obvious: “great, now bolt on bias.” That would be premature.

If bias lands on top of a half-clean preview contract and a slightly mushy legend story, the repo will start making stronger claims with weaker semantics. That’s exactly backwards.

---

## What should explicitly NOT be done next

### Do **not** do these next
- **Do not add bias and tone together.** That would be clown-car scope.
- **Do not add a generic multi-lens builder.** One good lens beats three half-honest ones.
- **Do not invent confidence sliders yet.** The current slice is not mature enough for that kind of theater.
- **Do not turn pending/failed/limited into direct filter values yet.** They belong in diagnostics/legend first, not as user-facing taxonomy.
- **Do not rework the whole Explorer control bar.** It’s fine. Don’t “improve” it into sludge.

---

## Strengths

- real extension of the Phase 1 visual grammar instead of a parallel UX
- highlight vs filter semantics stay mostly honest
- article type is a genuinely useful first lens for this product
- active-match precedence is sane
- selected / hovered / neighbor emphasis still wins locally
- backend metadata and point preview made the feature real instead of decorative
- bounded scope discipline held, which frankly is half the battle on this repo

## Weaknesses / caveats

- contract is only partially ready for bias/tone; it hints at extension more than it cleanly enables it
- legend/copy is slightly more confident than the actual mark encoding for missing-data states
- `coverage.total` language is sloppy in the rail and should be corrected
- article-type color mode is useful, but still a bit “dots plus legend” rather than a richer analytical read

---

## Final call

**Approve with caveats.**

This slice is worth keeping and building on. It is coherent, useful, and not fake.

But the next smart move is **not** more lenses. The next smart move is tightening the contract and the honesty of the explanatory layer so bias can land on solid ground instead of on top of slightly messy semantics.
