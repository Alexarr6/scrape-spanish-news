- State: COMPLETE
- Current phase: Explorer improvement pass — implementation (iter/005)
- Last update: 2026-03-20 UTC

## Completed deliverables (this pass)
- Full audit of Explorer frontend code: `MapPanel.tsx`, `ExplorerPage.tsx`, `ExplorerContextRail.tsx`, `ExplorerControlBar.tsx`, `useExplorerData.ts`, `styles.css`, `lib/types.ts`
- Rendered render unreliability diagnosis: 7 concrete bugs identified with root-cause analysis and priority ranking
- Updated `UI_SPEC.md` (iter/005): Explorer section fully rewritten — render reliability hardening plan, camera/framing spec, 2D/3D behavior, visual encoding hierarchy, legend/help/context spec, responsive table, states table
- Updated `DESIGN_TOKENS.md` (iter/005): Added Explorer-specific Section 12 with point encoding palette (authoritative constants), seeded context chip styling, canvas background, loading treatment, dev diagnostic overlay
- Updated `COMPONENT_MAP.md` (iter/005): Explorer section fully rewritten — MapPanel precision fix targets, new `explorerColors.ts` utility, updated ExplorerContextRail with seeded chip + onboarding guide + source swatches, updated ExplorerPage, CSS change summary
- **Implemented all bug fixes and UX improvements (frontend.react builder pass)**

## Bugs fixed (all applied)
1. BUG-1 (Highest): CSS flex/grid height chain — added `min-height:0` + `overflow:hidden` to `.explorer-workspace`, explicit `height:100%` to `.map-canvas`
2. BUG-2 (High): React 18 StrictMode double-mount — `key="explorer-deck"` on `<DeckGL>` stabilizes instance identity
3. BUG-4 (Medium): Named view ID mismatch — removed view IDs; unnamed single-view mode matches un-keyed viewState correctly
4. BUG-5 (Medium): Layer ID changes on toggle — stable `id: 'semantic-points'`; updateTriggers handle all dynamic changes
5. BUG-6 (Lower): CSS `!important` conflicting with DeckGL canvas sizing — removed; flex chain provides correct dimensions
6. BUG-3 diagnostic: dev-mode canvas/zoom/bounds overlay added to `MapPanel` (conditional on `import.meta.env.DEV`)

## UX improvements applied
- `explorerColors.ts`: authoritative encoding constants (fill, stroke, alpha, radius) for all point states
- Point encoding hierarchy fully implemented: selected → neighbors → hovered → outlier → regular, with correct alpha/radius/stroke per state and selection context
- Camera hardening: auto-fit only on first load (dataLoaded guard), not on every filter change
- 3D orbit angles preserved across `focusSelected()` calls
- Tooltip: added cluster ID, outlier badge, edge-clamping to prevent canvas overflow
- Dev diagnostic overlay in MapPanel (`DEV` only): canvas dimensions, point count, zoom, bounds
- Context rail: seeded context chip (Stories→Explorer handoff), onboarding guide, mode-sensitive legend (source swatches, cluster colors), outlier badge in selection state
- Control bar: `'By source'`, `'By cluster'` labels, tooltip hints on 2D/3D, `'N points (updating)'` during filter refetch

## Not done (deferred)
- BUG-7: Orphaned `useExplorerBootstrap.ts` — not removed (not a render bug; safe to defer)
- BUG-3 zoom formula: verified by diagnostic log, formula unchanged; actual real-data verification requires API data available in browser
- Mobile bottom-sheet CSS transform pattern (out of scope for this pass)

## Build status
- `cd frontend && npm run build` — ✅ PASS (tsc + vite, 0 errors, 4.90s)
- 3 atomic commits applied on iter/004 branch

## Required next execution route
- → verify in browser with real API data (confirm BUG-3 zoom is correct for actual projection scale)
- → optional cleanup: delete/document `useExplorerBootstrap.ts`
