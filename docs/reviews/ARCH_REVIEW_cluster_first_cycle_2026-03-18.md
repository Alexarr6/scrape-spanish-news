# Architect review — cluster-first product cycle (Phases 1-4)

Date: 2026-03-18
Scope reviewed:
1. backend read APIs for story clusters + entity/tag filters
2. cluster-first frontend browsing/detail flow
3. professional layout + URL/state polish
4. bounded 2D/3D semantic explorer integration as secondary drill-down

## Short verdict
This was a good cycle.

The product is finally pointing in the right direction: **story clusters are the primary object**, and the semantic explorer is demoted to what it should be — a secondary analysis surface, not the fake-main interface. That is a much saner hierarchy for an actual news-comparison tool.

More importantly, the phase breakdown was mostly rollback-safe and commit-friendly. The backend read surface landed first, then the UI flow, then polish, then explorer handoff. That sequencing makes sense and did not require a giant all-or-nothing rewrite. Good.

The remaining problems are not "this architecture is wrong." They are mostly **state-model duplication, URL/router shortcuts, and some handoff decisions that are clever but slightly too clever**.

## What is working

### 1) Cluster-first hierarchy is the correct product call
The cluster browser now answers the first user question: **what story is being covered?**
Only after that does the product ask: **how do individual articles sit in semantic space?**

That order is correct. The explorer alone is visually interesting, but product-wise it is a blob of dots with weak editorial meaning unless anchored to a story first.

### 2) API layering is pretty coherent
The new `/api/v1/clusters` surface is boring in a good way:
- list endpoint with paging + filter params
- filters endpoint for populating UI controls
- detail endpoint for member inspection

That is easy to reason about and matches the frontend flow cleanly.

The response shapes are also mostly sensible:
- list items are summary-grade and lightweight enough
- detail includes members with tags/entities
- explorer article detail is reused as the article drill-down payload

This is not overdesigned. Good.

### 3) The frontend flow is now understandable
`ClusterBrowserPage` + `useClusterBrowserData` + `useClusterUrlState` form a coherent vertical slice.

The UI hierarchy also makes sense:
- left: filters
- middle: cluster list
- right: cluster/article inspection

That is miles better than leading with the semantic cloud and pretending users naturally think in PCA coordinates. They don’t.

### 4) The explorer remains bounded
The explorer did not metastasize into a second primary product. Good restraint.

The current handoff — "open this story/article in semantic explorer" — is the right level of ambition for this phase. It keeps the explorer available for drill-down without letting it hijack the whole app.

## Risks / design debt

### 1) URL/view routing is a shortcut, not a durable app shell
Right now the entire app is effectively switched by `view=semantic` in query params (`App.tsx` via `isSemanticExplorerMode()`).

That works for a bounded phase, but it is a hacky router substitute. It will get annoying once there are more product surfaces, saved views, compare pages, or richer back/forward behavior.

Blunt version: **query-string mode switching is fine for a prototype, not for the adult version of this app.**

### 2) URL state is coherent locally but duplicated across product surfaces
There are now two independent URL-state systems:
- `useClusterUrlState`
- `useExplorerUrlState`

And two distinct query vocabularies:
- plain params for cluster browser (`search`, `source`, `tag`, `entity`, etc.)
- `sem_*` params for explorer

That avoids collisions, which is good. But it also means the product now has two parallel state grammars and custom navigation rules.

That is manageable today, but it is the kind of thing that quietly turns into brittle spaghetti if you keep adding surfaces without introducing real route/state conventions.

### 3) Browser history behavior looks undercooked
Both URL-state hooks use `window.history.replaceState(...)`, and neither listens for `popstate`.

So yes, the URL updates. But the back button behavior is likely weaker than users expect, and the app state is not truly derived from navigation events after initial load.

That is a classic "looks polished until you actually use it like a user" problem.

### 4) Explorer handoff is useful but slightly too opinionated
`buildSemanticExplorerHref()` seeds explorer state from the cluster/article by stuffing in:
- `sem_search` from article title or cluster headline
- `sem_source` from article source
- `sem_from` / `sem_to` from cluster window
- selected article id

This is smart, but also risky.

Why? Because a handoff should usually preserve context without accidentally over-filtering the destination. Seeding the explorer with a full article title as search can become a stealth filter that narrows the dot cloud harder than the user intended.

In other words: the handoff is helpful, but it may be doing too much magic.

### 5) Read-side/API assembly is growing into a god-file pattern
`src/analysis/readside.py` is doing a lot already: list matching, count logic, summary shaping, detail shaping, tag/entity joins, filter option queries.

It is still readable, but the growth pattern is obvious. If the next few phases keep landing here, this file will become the place where every read concern goes to die.

No emergency yet — but the repo is approaching the point where cluster-query assembly deserves its own module boundary.

### 6) The explorer still has UX/framing rough edges
This was already observed in live usage: the point cloud framing/camera starts too far away relative to the actual data spread. The code is trying to fit bounds, but the initial zoom/focus heuristics still feel approximate rather than dependable.

This does not break the architecture, but it reinforces the decision to keep the explorer secondary. Right now it is useful, not yet effortless.

## Answers to the explicit review questions

### 1) Does the cluster-first product hierarchy make sense versus the semantic explorer?
Yes. Strong yes.

The cluster browser should be the default product surface. It is editorially legible and maps to the actual problem: compare coverage of the same event across outlets.

The semantic explorer is valuable, but as a secondary lens for proximity/outliers/neighbor context. Making it primary would be product cosplay.

### 2) Are the API shapes and frontend state/URL patterns coherent and maintainable?
Mostly yes, with caveats.

The API shapes are coherent.
The frontend state is understandable.
The URL patterns are serviceable.

But maintainability will start slipping if the app keeps growing on top of:
- query-param mode switching instead of routing
- duplicated URL-state hooks without shared conventions
- read-side aggregation concentrated in one expanding file

So: **coherent now, but only if the next phase tightens the seams instead of adding more parallel patterns.**

### 3) Does the explorer integration feel like a sane secondary flow, or does it create product confusion?
Mostly sane.

The copy and placement are doing the right thing: cluster browser first, explorer second. That is good product guidance.

The only real confusion risk is the handoff magic. If users land in the explorer and it already has seeded search/source/date constraints, they may not realize why they are seeing a narrowed subset.

### 4) What are the biggest risks/rough edges now?
In priority order:
1. fake-router query-param view switching
2. weak browser-history/back-button semantics
3. over-magical explorer handoff filters
4. growing readside aggregation complexity
5. explorer camera/framing roughness
6. state duplication across cluster/explorer flows

### 5) What should be the next bounded phase after this?
**Next bounded phase should be: navigation/state hardening, not another flashy feature.**

That phase should include:
- proper route split between cluster browser and semantic explorer
- shared URL/query helpers and explicit param ownership
- better back/forward behavior via real navigation state
- simplification of explorer handoff rules
- small read-side module cleanup for cluster queries/serializers

That is the highest-leverage cleanup phase because it makes future features cheaper instead of more fragile.

### 6) High-value fixes / simplifications / refactors worth doing soon
1. **Introduce real routes** for cluster browser vs semantic explorer.
   - Stop using `view=semantic` as the app switch.
2. **Simplify explorer handoff defaults.**
   - Prefer seeding date range + selected article/cluster context.
   - Be careful with auto-seeding full-text search or source filters unless clearly visible and intentional.
3. **Extract cluster read-side logic** into a dedicated module boundary.
   - Keep query building, filters loading, and response shaping from piling into one file forever.
4. **Unify URL-state conventions.**
   - Keep separate params if needed, but centralize parsing/serialization helpers.
5. **Add popstate-aware state sync** or move to actual router-backed search params.
6. **Tighten explorer fit/focus heuristics** so the secondary flow feels deliberate instead of fiddly.

## Recommended next steps in priority order
1. **Phase 5: navigation/state hardening**
   - real routes
   - cleaner search-param ownership
   - back/forward correctness
   - simpler cluster→explorer handoff
2. **Phase 6: read-side/API cleanup**
   - split cluster readside code into smaller modules
   - preserve current API contracts while reducing coupling
3. **Phase 7: cluster comparison UX pass**
   - better within-cluster source comparison cues
   - stronger member/article comparison affordances
   - only after routing/state foundations are solid
4. **Phase 8: explorer fit-and-guidance polish**
   - camera framing
   - visible explanation of seeded filters/context
   - optional cluster highlighting from handoff context

## Final recommendation
**Yes — this phased cycle is a good checkpoint.**

Not perfect, but absolutely a valid checkpoint.

Why:
- the product hierarchy is better
- the backend/frontend contracts line up
- the explorer is bounded instead of running the show
- the increments were mostly rollback-safe and commit-friendly

The cycle should be considered successful.

The only trap now would be getting seduced into adding more surface area before tightening navigation/state architecture. That would be dumb. Tighten the seams first, then keep building.
