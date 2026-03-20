# COMPONENT_MAP.md — iter/004 Component Architecture

**Role:** Frontend Architect (iter/004)
**Date:** 2026-03-20

---

## Overview

This map defines the full component inventory for the rebuilt frontend. It covers:
- what each component does and owns
- what props it receives
- which state it manages (if any)
- which existing component it replaces
- which other components it composes

Read alongside `UI_SPEC.md` (layout and screen specs) and `DESIGN_TOKENS.md` (visual system).

---

## 1. App entry and routing

### `App.tsx` (refactor)

**Role:** Root component. Renders shell + routes based on `isSemanticExplorerMode()`.

**Changes from current:**
- No longer passes `shell={AppShell}` as a prop to routes
- Simpler: `<Shell navItems={...}><ClusterBrowserPage /></Shell>` or `<Shell navItems={...}><ExplorerPage /></Shell>`
- `navItems` remains computed here from navigation lib

```tsx
// New shape
export default function App() {
  const navItems = buildNavItems()
  return (
    <Shell navItems={navItems}>
      {isSemanticExplorerMode() ? <ExplorerPage /> : <ClusterBrowserPage />}
    </Shell>
  )
}
```

---

## 2. Layout components (`components/layout/`)

### `Shell.tsx` ← replaces `AppShell.tsx`

**Role:** Renders the global app frame. Top bar + main content area only. No route logic.

**Props:**
```tsx
type ShellProps = {
  navItems: NavItem[]
  children: ReactNode
}
```

**Internal structure:**
```tsx
<div className="app-shell">
  <TopBar navItems={navItems} />
  <main className="app-main">{children}</main>
</div>
```

**CSS:**
```css
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
```

**Eliminates:** `app-sidebar`, `brand-block`, `sidebar-note`, `page-header`, `workspace-grid`, `workspace-panel` responsibility from shell.

---

### `TopBar.tsx` ← new

**Role:** Sticky global top bar with wordmark, nav, and optional dataset scope chip.

**Props:**
```tsx
type TopBarProps = {
  navItems: NavItem[]
  scopeLabel?: string  // optional — "15–20 Mar · 8 sources"
}
```

**Internal structure:**
```tsx
<header className="topbar">
  <span className="topbar-wordmark">Signal</span>
  <nav className="topbar-nav">
    {navItems.map(item => (
      <a key={item.key} href={item.href} className={item.active ? 'topbar-nav-item active' : 'topbar-nav-item'}>
        {item.label}
      </a>
    ))}
  </nav>
  {scopeLabel && <span className="badge muted topbar-scope">{scopeLabel}</span>}
</header>
```

**Behavior:**
- Sticky top, z-index above panels
- `scopeLabel` prop: pass if API returns scope info (optional for initial build; can be `undefined`)
- Active state: bottom border on active nav item, no background treatment

---

### `FilterDrawer.tsx` ← new (replaces `ClusterFilterPanel` + `FilterBar`)

**Role:** Slide-over filter panel shared by both routes. Content slots controlled by parent.

**Props:**
```tsx
type FilterDrawerProps = {
  open: boolean
  onClose: () => void
  title: string           // "Refine Stories" or "Refine Explorer"
  children: ReactNode     // filter fields from parent
  activeCount?: number    // badge on trigger button (managed by parent)
  onReset?: () => void
}
```

**Behavior:**
- Slides in from left (overlay) on `open=true`
- Backdrop click closes
- Escape key closes
- `onReset` shown as "Clear all" if provided
- Does NOT manage filter state — only renders provided children
- Mobile: full width overlay

**CSS:**
```css
.filter-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--filter-drawer-width, 340px);
  z-index: 100;
  background: var(--color-surface);
  box-shadow: var(--shadow-overlay);
  border-right: 1px solid var(--color-border-strong);
  display: flex;
  flex-direction: column;
  transform: translateX(-100%);
  transition: transform 220ms ease-out;
}
.filter-drawer.open {
  transform: translateX(0);
}
.filter-drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
  background: rgba(14, 23, 36, 0.25);
}
```

---

### `SectionDivider.tsx` ← new

**Role:** Thin semantic divider between named sections in a panel.

**Props:**
```tsx
type SectionDividerProps = {
  label?: string   // optional section label above the divider
}
```

Rendered as `<hr className="section-divider" />` with optional label above.

---

## 3. Stories route components (`components/stories/`)

### `StoryStream.tsx` ← heavily refactors `ClusterListPanel.tsx`

**Role:** Main column of Stories route. Renders story cards, pagination.

**Props:**
```tsx
type StoryStreamProps = {
  data: StoryClusterListResponse | null
  loading: boolean
  error: string | null
  selectedClusterId: number | null
  onSelectCluster: (clusterId: number) => void
  onNextPage: () => void
  onPreviousPage: () => void
}
```

**Internal structure:**
```tsx
<div className="story-stream">
  {/* Loading state */}
  {loading && !data && <StoryStreamSkeleton />}

  {/* Error state */}
  {error && <ErrorState message={error} hint="Try widening the date range or clearing filters." />}

  {/* Empty state */}
  {!loading && !error && data?.items.length === 0 && (
    <EmptyState
      title="No stories match the current filters"
      hint="Clear a filter or widen the date window."
    />
  )}

  {/* Story cards */}
  {(data?.items ?? []).map(cluster => (
    <StoryCard
      key={cluster.id}
      cluster={cluster}
      selected={selectedClusterId === cluster.id}
      onClick={() => onSelectCluster(cluster.id)}
    />
  ))}

  {/* Pagination */}
  {data && <StoryPagination data={data} onPrevious={onPreviousPage} onNext={onNextPage} />}
</div>
```

**Removes from current:**
- `story-hero` card with marketing copy inside the panel
- Nested `cluster-results-header` with its own header
- Replaces the panel-in-panel-in-panel nesting

---

### `StoryCard.tsx` ← new (was inline in ClusterListPanel)

**Role:** Individual story cluster card in the stream.

**Props:**
```tsx
type StoryCardProps = {
  cluster: StoryClusterListItem
  selected: boolean
  onClick: () => void
}
```

**Internal structure:**
```tsx
<button className={`story-card ${selected ? 'selected' : ''}`} onClick={onClick}>
  <div className="story-card-meta">
    <span className="text-eyebrow">{cluster.cluster_type.replace(/_/g, ' ')}</span>
    <span className="story-card-counts">
      {cluster.article_count} articles · {cluster.source_count} sources
    </span>
  </div>
  <h2 className="story-card-headline">{cluster.summary_headline}</h2>
  <p className="story-card-summary">{cluster.summary_text}</p>
  <div className="story-card-footer">
    <div className="story-card-sources">
      {cluster.sources.slice(0, 3).map(source => (
        <span key={source} className="badge">{source}</span>
      ))}
      {cluster.sources.length > 3 && (
        <span className="badge muted">+{cluster.sources.length - 3}</span>
      )}
    </div>
    <span className="story-card-date">{formatClusterWindow(cluster)}</span>
  </div>
</button>
```

**CSS rules:**
```css
.story-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  border-left: 3px solid transparent;
  text-align: left;
  cursor: pointer;
  transition: border-color 120ms ease, background 120ms ease;
}
.story-card:hover {
  border-color: var(--color-border-strong);
  background: var(--color-hover-bg);
}
.story-card.selected {
  border-left-color: var(--color-accent);
  background: var(--color-selected-bg);
}
.story-card-headline {
  font-size: var(--text-md);
  font-weight: 700;
  line-height: var(--leading-snug);
  color: var(--color-text);
}
.story-card-summary {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.story-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}
.story-card-sources {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.story-card-date {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}
```

---

### `StoryFocusPanel.tsx` ← replaces `ClusterInspectorPanel.tsx`

**Role:** Story focus panel. Shows story brief, coverage bar, articles by source, and selected article detail.

**Props:**
```tsx
type StoryFocusPanelProps = {
  detail: StoryClusterDetail | null
  article: ExplorerArticleDetail | null
  loading: boolean
  articleLoading: boolean
  error: string | null
  articleError: string | null
  selectedArticleId: number | null
  onSelectArticle: (articleId: number | null) => void  // null = back/clear
}
```

**Internal states rendered:**

1. `loading && !detail` → `<LoadingState label="Loading story…" />`
2. `error` → `<ErrorState message={error} />`
3. `!detail` → Empty state (editorial prompt + Explorer CTA)
4. `detail` → Full focus panel

**Full focus panel structure:**
```tsx
<div className="story-focus-panel">
  {/* Section 1: Story brief */}
  <section className="focus-brief">
    <span className="text-eyebrow">{cluster_type} · {status}</span>
    <h2>{summary_headline}</h2>
    <p>{summary_text}</p>
    <div className="focus-brief-meta">
      {article_count} articles · {source_count} sources · {date window}
    </div>
    <a href={explorerHref} className="btn-ghost focus-explorer-link">
      Open in Explorer →
    </a>
  </section>

  <SectionDivider label="Coverage" />

  {/* Section 2: Coverage bar */}
  <CoverageBar members={detail.members} />

  <SectionDivider label="Articles by source" />

  {/* Section 3: Articles by source */}
  {selectedArticleId ? (
    /* Section 4: Article detail */
    <ArticleDetailSection
      article={article}
      loading={articleLoading}
      error={articleError}
      onBack={() => onSelectArticle(null)}
    />
  ) : (
    <SourceGroupList
      members={detail.members}
      selectedArticleId={selectedArticleId}
      onSelectArticle={onSelectArticle}
    />
  )}
</div>
```

**Sub-components (can be in same file or split):**

**`CoverageBar`** — see below.

**`SourceGroupList`:** renders members grouped by source. Uses `groupMembersBySource()` util from existing code. Each source section is a plain `<section>` with source name as header (not a card with border+shadow).

**`ArticleDetailSection`:** renders the selected article evidence. Has Back button, article body, semantic metrics, neighbors.

---

### `CoverageBar.tsx` ← new

**Role:** Visual representation of source share within a story's member articles.

**Props:**
```tsx
type CoverageBarProps = {
  members: StoryClusterMemberItem[]
}
```

**Internal logic:**
```ts
// Derived purely from members — no new backend needed
function computeCoverage(members: StoryClusterMemberItem[]) {
  const groups = new Map<string, number>()
  for (const m of members) {
    groups.set(m.source, (groups.get(m.source) ?? 0) + 1)
  }
  const total = members.length
  return Array.from(groups.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([source, count]) => ({ source, count, pct: Math.round((count / total) * 100) }))
}
```

**Rendered output:**
```tsx
<div className="coverage-bar">
  {coverage.map(({ source, count, pct }) => (
    <div key={source} className="coverage-bar-row">
      <span className="coverage-bar-label">{source}</span>
      <div className="coverage-bar-track">
        <div className="coverage-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="coverage-bar-count">{count} · {pct}%</span>
    </div>
  ))}
</div>
```

**CSS:**
```css
.coverage-bar { display: flex; flex-direction: column; gap: var(--space-2); }
.coverage-bar-row { display: flex; align-items: center; gap: var(--space-3); }
.coverage-bar-label { font-size: var(--text-xs); width: 5rem; color: var(--color-text-secondary); }
.coverage-bar-track { flex: 1; height: 6px; background: var(--color-bg-subtle); border-radius: var(--radius-full); overflow: hidden; }
.coverage-bar-fill { height: 100%; background: var(--color-accent); border-radius: var(--radius-full); }
.coverage-bar-count { font-size: var(--text-xs); color: var(--color-text-muted); width: 4rem; text-align: right; }
```

---

## 4. Stories route page (`routes/ClusterBrowserPage.tsx`)

**Role:** Composes Stories layout. No longer receives `shell` prop.

**Internal layout:**
```tsx
<div className="stories-layout">
  <StoriesHeader
    total={listState.data?.meta.total ?? 0}
    sourceCount={?}            // optional — from filter data if available
    activeFilterCount={activeFilterCount}
    onOpenFilters={() => setFiltersOpen(true)}
  />

  <div className="stories-workspace">
    <StoryStream
      data={listState.data}
      loading={listState.loading}
      error={listState.error}
      selectedClusterId={selectedClusterId}
      onSelectCluster={setSelectedClusterId}
      onNextPage={...}
      onPreviousPage={...}
    />
    <StoryFocusPanel
      detail={detailState.data}
      article={articleState.data}
      loading={detailState.loading}
      articleLoading={articleState.loading}
      error={detailState.error}
      articleError={articleState.error}
      selectedArticleId={selectedArticleId}
      onSelectArticle={setSelectedArticleId}
    />
  </div>

  <FilterDrawer
    open={filtersOpen}
    onClose={() => setFiltersOpen(false)}
    title="Refine Stories"
    activeCount={activeFilterCount}
    onReset={resetQuery}
  >
    <StoriesFilterFields
      filters={filtersState.data}
      query={query}
      onQueryChange={updateQuery}
      disabled={listState.loading && !listState.data}
    />
  </FilterDrawer>
</div>
```

**Local state added:**
- `const [filtersOpen, setFiltersOpen] = useState(false)` — filter drawer toggle

**CSS layout:**
```css
.stories-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  max-width: var(--content-max);
  margin: 0 auto;
  width: 100%;
  padding: var(--space-6);
  gap: var(--space-5);
}
.stories-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) min(480px, 37vw);
  gap: var(--space-5);
  align-items: start;
}
```

**`StoriesHeader`** (inline or separate file):
```tsx
<header className="stories-header">
  <div>
    <h1 className="stories-title">Stories</h1>
    <p className="stories-scope">
      {total} stories in scope
      {sourceCount ? ` · ${sourceCount} sources` : ''}
    </p>
  </div>
  <div className="stories-header-actions">
    {activeFilterCount > 0 && (
      <span className="badge accent">{activeFilterCount} filters</span>
    )}
    <button className="btn-ghost" onClick={onOpenFilters}>Refine ↓</button>
  </div>
</header>
```

**`StoriesFilterFields`** (inline or separate file):
Direct port of `ClusterFilterPanel` fields without the panel wrapper. Fields render inside `FilterDrawer.children`.

---

## 5. Explorer route components (`components/explorer/`)

### `ExplorerControlBar.tsx` ← new

**Role:** Compact horizontal control bar above the Explorer canvas.

**Props:**
```tsx
type ExplorerControlBarProps = {
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  pointCount: number
  activeFilterCount: number
  loading: boolean
  onViewModeChange: (mode: ExplorerViewMode) => void
  onColorModeChange: (mode: ExplorerColorMode) => void
  onFitAll: () => void
  onFocusSelected: () => void
  onOpenFilters: () => void
  hasSelection: boolean
}
```

**Internal structure:**
```tsx
<div className="explorer-control-bar">
  <div className="explorer-controls-left">
    <SegmentedControl
      options={[{ value: '2d', label: '2D' }, { value: '3d', label: '3D' }]}
      value={viewMode}
      onChange={onViewModeChange}
    />
    <SegmentedControl
      options={[
        { value: 'neutral', label: 'Neutral' },
        { value: 'source', label: 'Source' },
        { value: 'cluster', label: 'Cluster' },
      ]}
      value={colorMode}
      onChange={onColorModeChange}
    />
    <button className="btn-ghost" onClick={onFitAll}>Fit all</button>
    {hasSelection && (
      <button className="btn-ghost" onClick={onFocusSelected}>Focus selected</button>
    )}
  </div>
  <div className="explorer-controls-right">
    <span className="explorer-point-count">{pointCount} points</span>
    {activeFilterCount > 0 && (
      <span className="badge accent">{activeFilterCount} filters</span>
    )}
    <button className="btn-ghost" onClick={onOpenFilters}>Refine ↓</button>
  </div>
</div>
```

**CSS:**
```css
.explorer-control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-6);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.explorer-controls-left, .explorer-controls-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.explorer-point-count {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
```

**Note on camera controls:** `onFitAll` and `onFocusSelected` must call into `MapPanel` via a ref (same as today's MapPanel internal pattern). Maintain that ref-based imperative interface.

---

### `ExplorerContextRail.tsx` ← replaces `InspectorPanel.tsx`

**Role:** Right context rail for Explorer. No selection tabs — sections with dividers.

**Props:**
```tsx
type ExplorerContextRailProps = {
  selectedPoint: ExplorerPoint | null
  detail: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  clusterSummaries: ExplorerClusterSummary[]
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onClearSelection: () => void
  onSelectArticle: (articleId: number) => void
}
```

**No-selection state:**
```tsx
<div className="context-rail">
  <div className="context-rail-guide">
    <p className="context-guide-text">Click any point to inspect an article and its semantic neighborhood.</p>
  </div>
  <SectionDivider label="Legend" />
  <ColorLegend colorMode={colorMode} clusterSummaries={clusterSummaries} />
  <SectionDivider label="Dataset" />
  <DatasetSummary clusterSummaries={clusterSummaries} />
</div>
```

**Selection state:**
```tsx
<div className="context-rail">
  <div className="context-rail-header">
    <button className="btn-text" onClick={onClearSelection}>← Clear</button>
  </div>

  {/* Article section */}
  <div className="context-article">
    <span className="text-eyebrow">{detail.article.source} · {detail.article.section}</span>
    <h3 className="context-article-title">{detail.article.title}</h3>
    <p className="context-article-date">{formatDate(detail.article.published_at)}</p>
    <p className="context-article-summary">{clampText(detail.article.summary, detail.article.article_text_excerpt)}</p>
    <div className="context-article-actions">
      <a href={detail.article.url} target="_blank" rel="noreferrer" className="btn-ghost">Open article ↗</a>
      {storiesHref && <a href={storiesHref} className="btn-ghost">Open in Stories →</a>}
    </div>
  </div>

  <SectionDivider label="Cluster context" />

  <ClusterContextSection summary={selectedCluster} />

  <SectionDivider label="Semantic neighborhood" />

  <NeighborhoodSection
    neighbors={detail.neighbors}
    onSelectArticle={onSelectArticle}
  />
</div>
```

**"Open in Stories" link construction:**
```ts
// In ExplorerContextRail or navigation.ts
function buildStoriesHref(point: ExplorerPoint | null): string | null {
  if (!point?.analysis.cluster_id) return null
  // Assumes ClusterBrowserPage can accept ?clusterId= in URL state
  return buildClusterBrowserHref({ clusterId: point.analysis.cluster_id })
}
```

**Note:** Requires `buildClusterBrowserHref` in `navigation.ts` to support `clusterId` param. Verify `useClusterUrlState` reads it on mount and sets `selectedClusterId`.

---

### `MapPanel.tsx` (refactor, keep file)

**Role:** DeckGL canvas. Controls moved out.

**Props change:**
- Remove `onViewModeChange` and `onColorModeChange` — those are now in `ExplorerControlBar`
- Remove `viewMode` and `colorMode` if MapPanel receives them purely for controls; keep if needed for rendering
- Add imperative ref handle for `fitAll` and `focusSelected`:

```tsx
// Expose imperative handle
export type MapPanelHandle = {
  fitAll: () => void
  focusSelected: () => void
}

const MapPanel = forwardRef<MapPanelHandle, MapPanelProps>((props, ref) => {
  useImperativeHandle(ref, () => ({
    fitAll: () => { /* existing fit logic */ },
    focusSelected: () => { /* existing focus logic */ },
  }))
  // ...
})
```

This allows `ExplorerPage` to pass the ref to `MapPanel` and call camera actions from `ExplorerControlBar` without prop drilling camera callbacks through the control bar.

**Canvas cleanliness:**
- Remove `.map-toolbar` overlay from inside the canvas
- Remove the guide text overlay from inside the canvas
- Keep: hover tooltip, empty state overlay (when no points), loading overlay

---

## 6. Explorer route page (`routes/ExplorerPage.tsx`)

**Role:** Composes Explorer layout. No longer receives `shell` prop.

**Internal layout:**
```tsx
<div className="explorer-layout">
  <ExplorerControlBar
    viewMode={viewMode}
    colorMode={colorMode}
    pointCount={pointsState.data?.meta.returned ?? 0}
    activeFilterCount={activeFilterCount}
    loading={pointsState.loading}
    onViewModeChange={setViewMode}
    onColorModeChange={setColorMode}
    onFitAll={() => mapRef.current?.fitAll()}
    onFocusSelected={() => mapRef.current?.focusSelected()}
    onOpenFilters={() => setFiltersOpen(true)}
    hasSelection={selectedArticleId !== null}
  />

  <div className="explorer-workspace">
    <div className="explorer-canvas-area">
      <MapPanel
        ref={mapRef}
        points={pointsState.data}
        loading={pointsState.loading}
        error={pointsState.error}
        selectedArticleId={selectedArticleId}
        hoveredArticleId={hoveredArticleId}
        neighborIds={neighborIds}
        viewMode={viewMode}
        colorMode={colorMode}
        onHoverArticle={setHoveredArticleId}
        onSelectArticle={setSelectedArticleId}
      />
    </div>

    <ExplorerContextRail
      selectedPoint={selectedPoint}
      detail={detailState.data}
      loading={detailState.loading}
      error={detailState.error}
      clusterSummaries={pointsState.data?.meta.cluster_summaries ?? filtersState.data?.cluster_summaries ?? []}
      viewMode={viewMode}
      colorMode={colorMode}
      onClearSelection={clearSelectedArticle}
      onSelectArticle={setSelectedArticleId}
    />
  </div>

  <FilterDrawer
    open={filtersOpen}
    onClose={() => setFiltersOpen(false)}
    title="Refine Explorer"
    activeCount={activeFilterCount}
    onReset={resetQuery}
  >
    <ExplorerFilterFields
      filters={filtersState.data}
      query={query}
      onQueryChange={updateQuery}
      disabled={pointsState.loading && !pointsState.data}
    />
  </FilterDrawer>
</div>
```

**Local state added:**
- `const [filtersOpen, setFiltersOpen] = useState(false)` — filter drawer toggle
- `const mapRef = useRef<MapPanelHandle>(null)` — imperative camera control

**CSS layout:**
```css
.explorer-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.explorer-workspace {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--explorer-context-width, 320px);
  align-items: stretch;
}
.explorer-canvas-area {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
```

---

## 7. Shared utility components (`components/system/`)

### `LoadingState.tsx`

```tsx
type Props = { label?: string; hint?: string }
// Renders: label + optional hint, minimal styling
```

### `ErrorState.tsx`

```tsx
type Props = { message: string; hint?: string; onRetry?: () => void }
// Renders: error message + hint + optional retry button
```

### `EmptyState.tsx`

```tsx
type Props = { title: string; hint?: string; action?: ReactNode }
// Renders: title + hint + optional action (button or link)
```

These consolidate the current mix of `.loading-card`, `.empty-state-card`, `.state-card error-state` patterns into consistent components.

---

## 8. Preserved components

These files survive with minimal or no changes.

| File | Status |
|---|---|
| `hooks/useClusterBrowserData.ts` | Keep |
| `hooks/useClusterUrlState.ts` | Keep (verify clusterId param support) |
| `hooks/useClusterFilters.ts` | Keep |
| `hooks/useExplorerData.ts` | Keep |
| `hooks/useExplorerUrlState.ts` | Keep |
| `hooks/useExplorerFilters.ts` | Keep |
| `hooks/useExplorerBootstrap.ts` | Keep |
| `lib/api.ts` | Keep (no new endpoints needed) |
| `lib/types.ts` | Keep (no new types needed for initial pass) |
| `lib/format.ts` | Keep |
| `lib/query.ts` | Keep |
| `lib/navigation.ts` | Minor: add clusterId param to `buildClusterBrowserHref` |

---

## 9. Components to delete

These are removed. The builder should delete the files and remove any imports.

| File | Replaced by |
|---|---|
| `components/AppShell.tsx` | `layout/Shell.tsx` + `layout/TopBar.tsx` |
| `components/ClusterStatusBar.tsx` | Inline in `StoriesHeader` (inside ClusterBrowserPage) |
| `components/StatusBar.tsx` | `ExplorerControlBar.tsx` |
| `components/ClusterFilterPanel.tsx` | `StoriesFilterFields` (inline) + `FilterDrawer.tsx` |
| `components/FilterBar.tsx` | `ExplorerFilterFields` (inline) + `FilterDrawer.tsx` |
| `components/ClusterListPanel.tsx` | `StoryStream.tsx` + `StoryCard.tsx` |
| `components/ClusterInspectorPanel.tsx` | `StoryFocusPanel.tsx` |
| `components/InspectorPanel.tsx` | `ExplorerContextRail.tsx` |

---

## 10. Build-level notes for builder

- `npm run build` should pass cleanly throughout. Do not let TypeScript errors accumulate.
- If `MapPanel` is refactored to use `forwardRef`, remember to update the import in `ExplorerPage`.
- `FilterDrawer` uses `position: fixed` — ensure it does not conflict with DeckGL's canvas `z-index`.
- The `isSemanticExplorerMode()` routing logic in `App.tsx` is fine for now. Do not introduce a full router.
- Do not add new npm packages unless strictly necessary. The current deps are sufficient.

---

*Component map complete. See UI_SPEC.md for layout specs and DESIGN_TOKENS.md for visual system.*
