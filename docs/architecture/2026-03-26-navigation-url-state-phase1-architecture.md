# Frontend navigation + URL-state phase 1 — architecture handoff (2026-03-26)

This is a seam-tightening pass, not a router project.

The current behavior mostly works, but the ownership is smeared across `App.tsx`, both URL hooks, and `navigation.ts`. That is how harmless query params turn into weird app-shell debt.

## Decision summary

Approve a bounded phase-1 refactor with four moves:

1. **Centralize app-mode ownership in one tiny helper layer** used by `App.tsx`.
2. **Extract shared URL mechanics** into small parse/serialize utilities.
3. **Keep Stories and Explorer state separate** as two explicit URL-state domains.
4. **Narrow `navigation.ts` to explicit cross-surface handoff builders** instead of clone-and-pray param mutation.

Do **not** add React Router, a global store, or a generic mega query-state abstraction.

## What the current code is actually doing

### `App.tsx`
- reads mode from ambient URL state through `isSemanticExplorerMode()`
- computes nav items once at module scope from `window.location.search`
- independently reads mode again during render to choose `ExplorerPage` vs `ClusterBrowserPage`

That means the shell has **no single source of truth** for app mode.

### `useClusterUrlState.ts`
- owns Stories query + selected cluster/article correctly
- duplicates integer parsing and URL rewrite mechanics
- rewrites only Stories-owned keys, which is good

### `useExplorerUrlState.ts`
- owns Explorer query + selected article + visual/editorial state correctly
- also duplicates parsing and URL rewrite mechanics
- forces `view=semantic`, which is fine for Explorer ownership

### `navigation.ts`
- decides mode with `isSemanticExplorerMode()`
- builds cross-surface URLs by cloning current params and deleting some keys
- preserves useful state in places, but the contract is implicit instead of declared

That last bit is the dangerous one. It works until somebody adds one more param and accidentally teaches a different surface to inherit garbage.

## Approved ownership model

## 1. App mode belongs to the app shell

Create a tiny app-mode layer under `frontend/src/lib/`.

Recommended shape:

```ts
type AppMode = 'stories' | 'explorer'

function getAppModeFromSearch(search?: string): AppMode
function isExplorerModeSearch(search?: string): boolean
function buildAppModeHref(mode: AppMode): string
```

### Rules
- `view=semantic` => `explorer`
- anything else => `stories`
- `App.tsx` reads mode once per render
- `App.tsx` derives both nav active state and page rendering from that one mode value
- nav items should be built inside the component from the resolved mode, not frozen at module scope

### Explicit non-goal
This helper is **not** a mini router. It owns only top-level surface mode.

## 2. Shared URL utilities own mechanics, not product meaning

Create one small shared helper module for search-param mechanics.

Recommended shape:

```ts
function readSearchParams(search?: string): URLSearchParams
function writeSearchParams(params: URLSearchParams): void
function deleteParams(params: URLSearchParams, keys: readonly string[]): void
function parseStrictPositiveInt(value: string | null, fallback: number): number
function parseNonNegativeInt(value: string | null, fallback: number): number
function parseOptionalPositiveInt(value: string | null): number | null
```

### Rules
- utilities may know about browser URL mechanics
- utilities may know about generic integer parsing
- utilities may preserve `pathname` + `hash`
- utilities must **not** encode Stories vs Explorer semantics
- no generic "surface state" blob serializer nonsense

That split matters. Shared scaffolding: yes. Shared semantic model: absolutely not.

## 3. Stories and Explorer remain separate URL-state domains

The hooks should share a skeleton, not a brain.

### Stories hook owns
- `search`
- `source`
- `tag`
- `entity`
- `from`
- `to`
- `limit`
- `offset`
- `cluster`
- `article`

### Explorer hook owns
- `view=semantic`
- `sem_search`
- `sem_source`
- `sem_section`
- `sem_cluster`
- `sem_story_cluster`
- `sem_from`
- `sem_to`
- `sem_outliers`
- `sem_limit`
- `sem_article`
- `sem_mode`
- `sem_color`
- `sem_editorial_dim`
- `sem_editorial_value`

### Hook structure requirement
Both hooks should follow the same internal pattern:

1. read current params with shared helpers
2. parse only their own domain keys
3. hold local React state in domain types
4. on state change, clone current params
5. delete only their own owned keys
6. write back only their own domain keys
7. serialize through one shared URL writer

This preserves mixed-URL survivability without pretending both surfaces have the same state model.

## 4. `navigation.ts` becomes explicit handoff builders

`navigation.ts` should stop being a vague bag of param edits.

Approve a narrower split like this:

```ts
function buildStoriesSurfaceHref(options?: {
  clusterId?: number | null
}): string

function buildExplorerSurfaceHref(options?: {
  storyClusterId?: number | null
  articleId?: number | null
}): string
```

The builders may internally seed from cluster/detail/article inputs if that keeps call sites clean, but the produced URL contract must stay explicit.

### Stories handoff contract
Stories destination builder may:
- remove `view`
- optionally set `cluster`
- leave unrelated Explorer params survivable unless the implementation chooses to clear Explorer-owned keys deliberately as cleanup

For phase 1, the important invariant is that **Stories mode wins once `view` is gone**.

### Explorer handoff contract
Explorer destination builder must:
- set `view=semantic`
- optionally seed `sem_story_cluster`
- optionally seed `sem_article`
- set seeded visual defaults expected by the current product:
  - `sem_mode=highlight`
  - `sem_color=active-match`
- clear incompatible seeded-transition params:
  - `sem_search`
  - `sem_source`
  - `sem_from`
  - `sem_to`
  - `sem_cluster`
  - `sem_section`
  - `sem_outliers`
  - `sem_editorial_dim`
  - `sem_editorial_value`

### Important subtlety
Do **not** collapse this into a universal `buildHref(surface, state)` helper. That is just router-creep wearing fake glasses.

## Invariants to preserve

## A. Mode selection
- Stories is default when `view=semantic` is absent.
- Explorer is active only when `view=semantic` is present.
- top nav active state and rendered page come from the same resolved app mode.

## B. Deep-link survival
- plain Stories URLs still open Stories
- explicit Explorer URLs still open Explorer
- refresh preserves current surface and that surface's URL-driven state
- mixed-surface URLs remain survivable because each hook only reads its own keys

## C. Seeded transitions
- Stories -> Explorer keeps the approved seeded drill-in behavior
- Explorer -> Stories drops semantic mode cleanly
- no accidental carryover of unrelated filter state as hidden coupling

## File-level implementation handoff

### `frontend/src/App.tsx`
- move nav item construction inside `App`
- replace repeated `isSemanticExplorerMode()` calls with one `const appMode = getAppModeFromSearch()`
- render and active-nav decisions from `appMode`

### `frontend/src/lib/`
Add one small helper module for:
- app-mode parsing/building
- shared URL search read/write helpers

One file or two tiny files are both fine. Do not explode this into a framework.

### `frontend/src/hooks/useClusterUrlState.ts`
- replace local parse helpers with shared integer parsers
- replace direct `history.replaceState` assembly with shared writer
- keep Stories field mapping local to the hook

### `frontend/src/hooks/useExplorerUrlState.ts`
- same refactor pattern as Stories hook
- keep Explorer-only parsing local: visual/color/editorial parsing stays here unless a parser is truly generic

### `frontend/src/lib/navigation.ts`
- remove ambient mode-reading responsibility from this file if possible
- keep only explicit Stories/Explorer handoff builders
- make carried/cleared keys intentional and listed, not incidental side effects of cloning current params

## Scope guardrails

If implementation starts doing any of this, it is off the rails:
- adding route paths
- inventing route components for the two modes
- syncing popstate/back-button semantics beyond current scope
- abstracting both hooks into one hook factory
- renaming param schemes across the app
- touching broad page/component layout

## Verification checklist for frontend.react

1. Load a Stories URL with no `view` param.
2. Load an Explorer URL with `view=semantic` and existing `sem_*` params.
3. Confirm `App.tsx` nav active state matches rendered page in both cases.
4. Open Stories -> Explorer from a seeded cluster/article and confirm:
   - `view=semantic`
   - `sem_story_cluster` and/or `sem_article` present when expected
   - `sem_mode=highlight`
   - `sem_color=active-match`
   - old conflicting Explorer filters cleared
5. Switch Explorer -> Stories and confirm `view` is removed.
6. Refresh on both surfaces and confirm state survives.
7. Run `cd frontend && npm run build`.

## Final call

The right phase-1 architecture is boring on purpose:
- one app-mode owner
- one tiny shared URL-mechanics layer
- two separate surface state models
- one explicit handoff file

Anything bigger is a fake cleanup that turns into a routing side quest.