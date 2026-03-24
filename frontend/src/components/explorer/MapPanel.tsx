/**
 * MapPanel.tsx — DeckGL semantic canvas.
 *
 * Bug fixes applied in iter/005:
 *  BUG-1: flex/grid height chain — fixed in styles.css (min-height: 0)
 *  BUG-2: StrictMode double-mount — stable key="explorer-deck" on <DeckGL>
 *  BUG-4: Named view IDs mismatch — removed view IDs (unnamed single-view)
 *  BUG-5: Layer ID changes on every toggle — stable id: 'semantic-points'
 *  BUG-6: !important overrides — removed from styles.css
 *
 * Camera hardening:
 *  - Auto-fit only fires on first data load (null → data) or explicit fitAll()
 *  - Subsequent filter changes preserve the user's camera position
 *  - 3D orbit angles preserved across focusSelected() calls
 */

import { OrbitView, OrthographicView } from '@deck.gl/core'
import { LineLayer, PointCloudLayer, ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { formatDate } from '../../lib/format'
import {
  articleTypeColorForPreviewRgb,
  describeEditorialPreview,
  isEditorialValueMatch,
} from '../../lib/explorerEditorial'
import {
  AXIS_COLOR_2D,
  AXIS_GRID_COLOR_3D,
  AXIS_X_COLOR_3D,
  AXIS_Y_COLOR_3D,
  AXIS_Z_COLOR_3D,
  CLUSTER_NULL_COLOR,
  CLUSTER_OUTLIER_COLOR,
  CLUSTER_PALETTE,
  PC_SIZE_HOVERED,
  PC_SIZE_NEIGHBOR,
  PC_SIZE_OUTLIER,
  PC_SIZE_REGULAR,
  PC_SIZE_SELECTED,
  POINT_DEFAULT_STROKE,
  POINT_DEFAULT_STROKE_WIDTH,
  POINT_HOVERED_FILL,
  POINT_HOVERED_RADIUS_2D,
  POINT_HOVERED_STROKE,
  POINT_HOVERED_STROKE_WIDTH,
  POINT_NEIGHBOR_FILL,
  POINT_NEIGHBOR_RADIUS_2D,
  POINT_NEIGHBOR_STROKE,
  POINT_NEIGHBOR_STROKE_WIDTH,
  POINT_NON_MATCH_ALPHA_HIGHLIGHT,
  POINT_NON_MATCH_RADIUS_SCALE_HIGHLIGHT,
  POINT_NON_MATCH_STROKE,
  POINT_NON_MATCH_STROKE_WIDTH,
  POINT_OUTLIER_ALPHA_NO_SELECTION,
  POINT_OUTLIER_ALPHA_UNDER_SELECTION,
  POINT_OUTLIER_RADIUS_2D,
  POINT_RECEDING_STROKE,
  POINT_RECEDING_STROKE_WIDTH,
  POINT_REGULAR_ALPHA_NO_SELECTION,
  POINT_REGULAR_ALPHA_UNDER_SELECTION,
  POINT_REGULAR_RADIUS_2D,
  POINT_SELECTED_FILL,
  POINT_SELECTED_RADIUS_2D,
  POINT_SELECTED_STROKE,
  POINT_SELECTED_STROKE_WIDTH,
  SOURCE_COLORS,
  SOURCE_FALLBACK_COLOR,
} from '../../lib/explorerColors'
import type {
  ExplorerColorMode,
  ExplorerEditorialTarget,
  ExplorerPoint,
  ExplorerPointsResponse,
  ExplorerProjectionBounds,
  ExplorerViewMode,
  ExplorerVisualMode,
} from '../../lib/types'

export type MapPanelHandle = {
  fitAll: () => void
  focusSelected: () => void
}

type Props = {
  points: ExplorerPointsResponse | null
  loading: boolean
  error: string | null
  selectedArticleId: number | null
  hoveredArticleId: number | null
  neighborIds: Set<number>
  viewMode: ExplorerViewMode
  visualMode: ExplorerVisualMode
  colorMode: ExplorerColorMode
  activeMatchTarget:
    | { type: 'editorial'; dimension: 'article_type'; value: string }
    | { type: 'story-cluster'; id: number; available: boolean }
    | { type: 'semantic-cluster'; id: number }
    | { type: 'search'; query: string }
    | { type: 'source'; source: string }
    | null
  editorialTarget: ExplorerEditorialTarget
  onHoverArticle: (articleId: number | null) => void
  onSelectArticle: (articleId: number | null) => void
}

type TooltipState = { x: number; y: number; point: ExplorerPoint } | null
type PickingInfoLike = { object?: ExplorerPoint; x?: number; y?: number }
type ViewState2D = { target: [number, number, number]; zoom: number }
type ViewState3D = { target: [number, number, number]; zoom: number; rotationOrbit: number; rotationX: number }
type ViewStateMap = { '2d': ViewState2D; '3d': ViewState3D }
type PointBounds = {
  minX: number; maxX: number; minY: number; maxY: number; minZ: number; maxZ: number
}

const DEFAULT_3D_ORBIT = 28
const DEFAULT_3D_TILT = 32

// ─── Bounds helpers ──────────────────────────────────────────────────────────

function normalizeBounds(bounds: ExplorerProjectionBounds | null): PointBounds | null {
  if (!bounds) return null
  return {
    minX: bounds.min_x, maxX: bounds.max_x,
    minY: bounds.min_y, maxY: bounds.max_y,
    minZ: bounds.min_z, maxZ: bounds.max_z,
  }
}

function boundsFromPoints(items: ExplorerPoint[]): PointBounds | null {
  if (items.length === 0) return null
  return items.reduce<PointBounds>(
    (acc, p) => ({
      minX: Math.min(acc.minX, p.x), maxX: Math.max(acc.maxX, p.x),
      minY: Math.min(acc.minY, p.y), maxY: Math.max(acc.maxY, p.y),
      minZ: Math.min(acc.minZ, p.z), maxZ: Math.max(acc.maxZ, p.z),
    }),
    { minX: items[0].x, maxX: items[0].x, minY: items[0].y, maxY: items[0].y, minZ: items[0].z, maxZ: items[0].z },
  )
}

// ─── ViewState builders ──────────────────────────────────────────────────────

// Padding factors: percentage of canvas the data span should occupy (inverted).
// 1.25 → data occupies 80% of canvas (10% margin per side) in 2D.
// 1.4  → slightly more padding in 3D for depth comfort.
const PADDING_2D = 1.25
const PADDING_3D = 1.4

/**
 * Read the canvas element's tighter dimension (width vs height) at call time.
 * Falls back to 900 (sensible for a ~900px canvas default) when DOM not yet ready.
 */
function getCanvasPx(canvasRef: React.RefObject<HTMLDivElement>): number {
  const el = canvasRef.current
  if (!el || el.clientWidth === 0 || el.clientHeight === 0) return 900
  return Math.min(el.clientWidth, el.clientHeight)
}

/**
 * Pixel-aware zoom formula (iter/006 fix).
 *
 * DeckGL OrthographicView semantics: at zoom Z, one world unit renders as 2^Z pixels.
 * To fit `paddedSpan` world units into `canvasPx` pixels:
 *   zoom = log2(canvasPx / paddedSpan)
 *
 * For real projection data in [-1, 1]:
 *   dominantSpan ≈ 2.0, paddedSpan ≈ 2.5, canvasPx ≈ 900 → zoom ≈ 8.5 ✓
 */
function build2dViewState(bounds: PointBounds | null, canvasPx: number): ViewState2D {
  if (!bounds) return { target: [0, 0, 0], zoom: 8.5 }  // sensible default for [-1,1] scale
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const dominantSpan = Math.max(spanX, spanY)
  const paddedSpan = Math.max(dominantSpan * PADDING_2D, 0.01)  // guard against zero-span
  return {
    target: [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2, 0],
    zoom: Math.max(1.0, Math.min(14.0, Math.log2(canvasPx / paddedSpan))),
  }
}

function build3dViewState(bounds: PointBounds | null, canvasPx: number, current?: ViewState3D): ViewState3D {
  if (!bounds) return {
    target: [0, 0, 0],
    zoom: 8.5,
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const spanZ = bounds.maxZ - bounds.minZ
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  const paddedSpan = Math.max(dominantSpan * PADDING_3D, 0.01)
  return {
    target: [
      (bounds.minX + bounds.maxX) / 2,
      (bounds.minY + bounds.maxY) / 2,
      (bounds.minZ + bounds.maxZ) / 2,
    ],
    zoom: Math.max(1.0, Math.min(14.0, Math.log2(canvasPx / paddedSpan))),
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
}

function buildInitialViewState(
  points: ExplorerPointsResponse | null,
  canvasPx: number,
  current?: ViewStateMap,
): ViewStateMap {
  const bounds = normalizeBounds(points?.meta.bounds ?? null)
  return {
    '2d': build2dViewState(bounds, canvasPx),
    '3d': build3dViewState(bounds, canvasPx, current?.['3d']),
  }
}

function buildSelectionBounds(selectedPoint: ExplorerPoint, items: ExplorerPoint[], neighborIds: Set<number>): PointBounds {
  const related = items.filter((item) =>
    item.article_id === selectedPoint.article_id || neighborIds.has(item.article_id),
  )
  const selectionBounds = boundsFromPoints(related.length > 0 ? related : [selectedPoint])
  if (!selectionBounds) {
    return {
      minX: selectedPoint.x, maxX: selectedPoint.x,
      minY: selectedPoint.y, maxY: selectedPoint.y,
      minZ: selectedPoint.z, maxZ: selectedPoint.z,
    }
  }
  return selectionBounds
}


function normalizeSearchText(value: string) {
  return value.trim().toLowerCase()
}

function pointMatchesActiveTarget(point: ExplorerPoint, activeMatchTarget: Props['activeMatchTarget']): boolean {
  if (!activeMatchTarget) return false
  if (activeMatchTarget.type === 'editorial') {
    return isEditorialValueMatch(point, { dimension: activeMatchTarget.dimension, value: activeMatchTarget.value })
  }
  if (activeMatchTarget.type === 'story-cluster') {
    return activeMatchTarget.available && (point.analysis.story_cluster_ids ?? []).includes(activeMatchTarget.id)
  }
  if (activeMatchTarget.type === 'semantic-cluster') return point.analysis.cluster_id === activeMatchTarget.id
  if (activeMatchTarget.type === 'source') return point.source === activeMatchTarget.source
  const haystack = `${point.title} ${point.summary_snippet}`.toLowerCase()
  return haystack.includes(normalizeSearchText(activeMatchTarget.query))
}

// ─── Color helpers ───────────────────────────────────────────────────────────

function colorForPoint(point: ExplorerPoint, mode: ExplorerColorMode): [number, number, number] {
  if (mode === 'source') {
    return SOURCE_COLORS[point.source] ?? SOURCE_FALLBACK_COLOR
  }
  if (mode === 'cluster') {
    if (point.analysis.cluster_id == null) {
      return point.analysis.is_outlier ? CLUSTER_OUTLIER_COLOR : CLUSTER_NULL_COLOR
    }
    return CLUSTER_PALETTE[(point.analysis.cluster_id - 1) % CLUSTER_PALETTE.length]
  }
  if (mode === 'article-type') {
    return articleTypeColorForPreviewRgb(point.editorial_preview)
  }
  // neutral
  return [67, 56, 202] // indigo-700
}

// ─── Axis layers ─────────────────────────────────────────────────────────────

type AxisLine2D = { from: [number, number, number]; to: [number, number, number] }
type AxisLine3D = { from: [number, number, number]; to: [number, number, number]; color: [number, number, number, number] }

/**
 * Build DeckGL axis orientation layers.
 * Always placed first in the layer stack so points render on top.
 * Uses LineLayer (already in @deck.gl/layers — no new packages).
 */
function buildAxisLayers(viewMode: ExplorerViewMode, bounds: PointBounds | null) {
  const extent = bounds
    ? Math.max(1.5, Math.max(
        Math.abs(bounds.minX), Math.abs(bounds.maxX),
        Math.abs(bounds.minY), Math.abs(bounds.maxY),
      ) * 1.1)
    : 1.5

  if (viewMode === '2d') {
    const axisData: AxisLine2D[] = [
      { from: [-extent, 0, 0], to: [extent, 0, 0] },   // X axis
      { from: [0, -extent, 0], to: [0, extent, 0] },   // Y axis
    ]
    return [
      new LineLayer<AxisLine2D>({
        id: 'axis-2d',
        data: axisData,
        getSourcePosition: (d) => d.from,
        getTargetPosition: (d) => d.to,
        getColor: AXIS_COLOR_2D,
        getWidth: 1.0,
        widthUnits: 'pixels',
        pickable: false,
      }),
    ]
  }

  // 3D: RGB-convention XYZ axes + faint XY plane grid
  const axisData: AxisLine3D[] = [
    { from: [-extent, 0, 0], to: [extent, 0, 0], color: AXIS_X_COLOR_3D },  // X red
    { from: [0, -extent, 0], to: [0, extent, 0], color: AXIS_Y_COLOR_3D },  // Y green
    { from: [0, 0, -extent], to: [0, 0, extent], color: AXIS_Z_COLOR_3D },  // Z blue
  ]

  // XY plane grid — faint lines at integer intervals to aid depth perception
  const gridExtent = Math.ceil(extent)
  const gridLines: AxisLine3D[] = []
  for (let i = -gridExtent; i <= gridExtent; i++) {
    gridLines.push(
      { from: [-extent, i, 0], to: [extent, i, 0], color: AXIS_GRID_COLOR_3D },
      { from: [i, -extent, 0], to: [i, extent, 0], color: AXIS_GRID_COLOR_3D },
    )
  }

  return [
    new LineLayer<AxisLine3D>({
      id: 'axis-grid-3d',
      data: gridLines,
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: (d) => d.color,
      getWidth: 0.8,
      widthUnits: 'pixels',
      pickable: false,
    }),
    new LineLayer<AxisLine3D>({
      id: 'axis-3d',
      data: axisData,
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: (d) => d.color,
      getWidth: 1.5,
      widthUnits: 'pixels',
      pickable: false,
    }),
  ]
}

// ─── Component ───────────────────────────────────────────────────────────────

export const MapPanel = forwardRef<MapPanelHandle, Props>(function MapPanel(
  {
    points,
    loading,
    error,
    selectedArticleId,
    hoveredArticleId,
    neighborIds,
    viewMode,
    visualMode,
    colorMode,
    activeMatchTarget,
    editorialTarget,
    onHoverArticle,
    onSelectArticle,
  },
  ref,
) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)
  // Initial useState call happens before canvasRef is populated — fallback 900 is acceptable;
  // the useEffect on first data load will re-fit with real DOM dimensions.
  const [viewState, setViewState] = useState<ViewStateMap>(() => buildInitialViewState(points, 900))
  const [dataLoaded, setDataLoaded] = useState(false)
  const canvasRef = useRef<HTMLDivElement>(null)

  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')

  const selectedPoint = useMemo(
    () => points?.items.find((item) => item.article_id === selectedArticleId) ?? null,
    [points, selectedArticleId],
  )
  const hasSelection = selectedArticleId != null
  // hasActiveMatch: true when there is a seed target that produces meaningful point differentiation.
  // For story-cluster, we require metadata to be available on the loaded points — otherwise
  // we have a seed but can't distinguish matches, so highlight mode is a no-op until data arrives.
  // The separate hasSeedContext flag lets us show a pending state in the rail without fully degrading.
  const hasActiveMatch = activeMatchTarget != null && (activeMatchTarget.type !== 'story-cluster' || activeMatchTarget.available)
  const visibleItems = useMemo(() => {
    const items = points?.items ?? []
    if (visualMode !== 'filter' || !hasActiveMatch) return items
    return items.filter((point) =>
      pointMatchesActiveTarget(point, activeMatchTarget) ||
      point.article_id === selectedArticleId ||
      neighborIds.has(point.article_id) ||
      point.article_id === hoveredArticleId,
    )
  }, [points, visualMode, hasActiveMatch, activeMatchTarget, selectedArticleId, neighborIds, hoveredArticleId])

  // ─── Camera auto-fit: ONLY fires on first data load (null → populated)
  // Subsequent filter changes preserve user camera position.
  const projectionSet = points?.meta.projection_set
  useEffect(() => {
    if (!points?.items.length) {
      setDataLoaded(false)
      return
    }
    if (!dataLoaded) {
      // First load or after a full reset — fit to all points with real canvas dimensions
      const px = getCanvasPx(canvasRef)
      setViewState((current) => buildInitialViewState(points, px, current))
      setDataLoaded(true)
    }
    // Subsequent filter changes: do NOT reset camera — user's pan/zoom is preserved
  }, [points?.items.length, projectionSet]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Imperative camera controls ──────────────────────────────────────────
  const fitAll = () => {
    const px = getCanvasPx(canvasRef)
    setViewState((current) => buildInitialViewState(points, px, current))
  }

  const focusSelected = () => {
    if (!selectedPoint) return
    const px = getCanvasPx(canvasRef)
    const selectionBounds = buildSelectionBounds(selectedPoint, points?.items ?? [], neighborIds)
    const focused2d = build2dViewState(selectionBounds, px)
    const focused3d = build3dViewState(selectionBounds, px, viewState['3d'])
    setViewState((current) => ({
      '2d': { ...focused2d, zoom: Math.min(focused2d.zoom + 0.25, 6.8) },
      '3d': {
        ...focused3d,
        zoom: Math.min(focused3d.zoom + 0.2, 6.2),
        // Preserve user's orbital angles — do not reset tilt/orbit on focus
        rotationOrbit: current['3d'].rotationOrbit,
        rotationX: current['3d'].rotationX,
      },
    }))
  }

  useImperativeHandle(ref, () => ({ fitAll, focusSelected }))

  // ─── Dev diagnostic (mount only) ─────────────────────────────────────────
  useEffect(() => {
    if (!import.meta.env.DEV) return
    const el = canvasRef.current
    // eslint-disable-next-line no-console
    console.debug(
      '[MapPanel] mount diagnostic:',
      '\n  canvas clientHeight:', el?.clientHeight ?? 'NOT FOUND',
      '\n  canvas clientWidth:', el?.clientWidth ?? 'NOT FOUND',
      '\n  points count:', points?.items.length ?? 0,
      '\n  viewState 2d:', viewState['2d'],
      '\n  bounds:', points?.meta.bounds,
    )
  }, []) // intentionally run once on mount only

  // ─── Layer ───────────────────────────────────────────────────────────────
  const layers = useMemo(() => {
    const items = visibleItems
    const bounds = normalizeBounds(points?.meta.bounds ?? null)

    // Axis layers always first — points render on top
    const axisLayers = buildAxisLayers(viewMode, bounds)

    // ─── 3D mode: PointCloudLayer tiers (billboarded volumetric spheres) ──────
    if (viewMode === '3d') {
      const isHighlighted = (p: ExplorerPoint) =>
        p.article_id === selectedArticleId ||
        neighborIds.has(p.article_id) ||
        p.article_id === hoveredArticleId

      const getPC3dColor = (p: ExplorerPoint): [number, number, number, number] => {
        if (p.article_id === selectedArticleId) return POINT_SELECTED_FILL
        if (neighborIds.has(p.article_id)) return POINT_NEIGHBOR_FILL
        if (p.article_id === hoveredArticleId) return POINT_HOVERED_FILL
        const isActiveMatch = pointMatchesActiveTarget(p, activeMatchTarget)
        const [r, g, b] = colorMode === 'active-match'
          ? isActiveMatch
            ? [124, 58, 237]
            : [148, 163, 184]
          : colorForPoint(p, colorMode)
        // Highlight mode: non-matches stay visible as context (~43% alpha), not hidden.
        // Filter mode uses the same receded alpha but hides them via visibleItems filtering.
        // Under selection: standard recede applies on top of any highlight logic.
        const alpha = hasActiveMatch && visualMode === 'highlight' && !isActiveMatch
          ? POINT_NON_MATCH_ALPHA_HIGHLIGHT
          : hasSelection
          ? p.analysis.is_outlier
            ? POINT_OUTLIER_ALPHA_UNDER_SELECTION
            : POINT_REGULAR_ALPHA_UNDER_SELECTION
          : p.analysis.is_outlier
            ? POINT_OUTLIER_ALPHA_NO_SELECTION
            : POINT_REGULAR_ALPHA_NO_SELECTION
        return [r, g, b, alpha]
      }

      const colorTrigger = [visualMode, colorMode, selectedArticleId, hoveredArticleId, neighborKey, hasSelection, hasActiveMatch, JSON.stringify(activeMatchTarget)]

      // Shared hover/click handlers for all PC tiers
      const pcOnHover = (info: PickingInfoLike) => {
        const point = info.object
        onHoverArticle(point?.article_id ?? null)
        if (point && info.x != null && info.y != null) {
          setTooltip({ x: info.x, y: info.y, point })
        } else {
          setTooltip(null)
        }
      }
      const pcOnClick = (info: PickingInfoLike) => onSelectArticle(info.object?.article_id ?? null)

      const pcLayer = (id: string, data: ExplorerPoint[], size: number) =>
        new PointCloudLayer<ExplorerPoint>({
          id,
          data,
          pickable: true,
          sizeUnits: 'pixels',
          pointSize: size,
          getPosition: (p) => [p.x, p.y, p.z],
          getColor: getPC3dColor,
          getNormal: [0, 0, 1],   // unused for billboard mode, required by API
          material: false,         // disable Phong — pure flat color preserves encoding
          onHover: pcOnHover,
          onClick: pcOnClick,
          updateTriggers: {
            getColor: colorTrigger,
          },
        })

      // Split into tiers — layer order: regular (back) → outlier → neighbor → hovered → selected (top)
      const regular  = items.filter(p => !isHighlighted(p) && !p.analysis.is_outlier)
      const outlier  = items.filter(p => !isHighlighted(p) && p.analysis.is_outlier)
      const neighbor = items.filter(p => neighborIds.has(p.article_id))
      const hovered  = hoveredArticleId != null ? items.filter(p => p.article_id === hoveredArticleId) : []
      const selected = selectedArticleId != null ? items.filter(p => p.article_id === selectedArticleId) : []

      return [
        ...axisLayers,
        pcLayer('pc-regular',  regular,  PC_SIZE_REGULAR),
        pcLayer('pc-outlier',  outlier,  PC_SIZE_OUTLIER),
        pcLayer('pc-neighbor', neighbor, PC_SIZE_NEIGHBOR),
        pcLayer('pc-hovered',  hovered,  PC_SIZE_HOVERED),
        pcLayer('pc-selected', selected, PC_SIZE_SELECTED),
      ]
    }

    // ─── 2D mode: ScatterplotLayer (stroked circles, correct for flat view) ───
    return [
      ...axisLayers,
      new ScatterplotLayer<ExplorerPoint>({
        id: 'semantic-points', // stable ID — updateTriggers handle all changes (BUG-5 fix)
        data: items,
        pickable: true,
        filled: true,
        stroked: true,
        opacity: 0.9,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        radiusMinPixels: 2,
        radiusMaxPixels: 18,

        getPosition: (point: ExplorerPoint) => [point.x, point.y],

        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_RADIUS_2D
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_RADIUS_2D
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_RADIUS_2D
          // Highlight mode: non-matches shrink slightly so matches stand out by size too.
          if (hasActiveMatch && visualMode === 'highlight' && !pointMatchesActiveTarget(point, activeMatchTarget)) {
            const base = point.analysis.is_outlier ? POINT_OUTLIER_RADIUS_2D : POINT_REGULAR_RADIUS_2D
            return Math.round(base * POINT_NON_MATCH_RADIUS_SCALE_HIGHLIGHT)
          }
          if (point.analysis.is_outlier) return POINT_OUTLIER_RADIUS_2D
          return POINT_REGULAR_RADIUS_2D
        },

        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_FILL
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_FILL
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_FILL
          const isActiveMatch = pointMatchesActiveTarget(point, activeMatchTarget)
          const [r, g, b] = colorMode === 'active-match'
            ? isActiveMatch
              ? [124, 58, 237]
              : [148, 163, 184]
            : colorForPoint(point, colorMode)
          // Highlight mode: non-matches stay visible as context (~43% alpha), not hidden.
          // This is intentionally gentler than filter mode so the map reads as
          // "everything visible, matches pulled forward" not "everything else gone".
          const alpha = hasActiveMatch && visualMode === 'highlight' && !isActiveMatch
            ? POINT_NON_MATCH_ALPHA_HIGHLIGHT
            : hasSelection
            ? point.analysis.is_outlier
              ? POINT_OUTLIER_ALPHA_UNDER_SELECTION
              : POINT_REGULAR_ALPHA_UNDER_SELECTION
            : point.analysis.is_outlier
              ? POINT_OUTLIER_ALPHA_NO_SELECTION
              : POINT_REGULAR_ALPHA_NO_SELECTION
          return [r, g, b, alpha] as [number, number, number, number]
        },

        getLineColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE
          // Highlight mode: non-matches get a very faint stroke so they read as context without vanishing.
          if (hasActiveMatch && visualMode === 'highlight' && !pointMatchesActiveTarget(point, activeMatchTarget)) {
            return POINT_NON_MATCH_STROKE
          }
          if (hasSelection) return POINT_RECEDING_STROKE
          return POINT_DEFAULT_STROKE
        },

        getLineWidth: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE_WIDTH
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE_WIDTH
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE_WIDTH
          // Highlight mode: non-matches get thin stroke consistent with context role.
          if (hasActiveMatch && visualMode === 'highlight' && !pointMatchesActiveTarget(point, activeMatchTarget)) {
            return POINT_NON_MATCH_STROKE_WIDTH
          }
          if (hasSelection) return POINT_RECEDING_STROKE_WIDTH
          return POINT_DEFAULT_STROKE_WIDTH
        },

        onHover: (info: PickingInfoLike) => {
          const point = info.object
          onHoverArticle(point?.article_id ?? null)
          if (point && info.x != null && info.y != null) {
            setTooltip({ x: info.x, y: info.y, point })
          } else {
            setTooltip(null)
          }
        },

        onClick: (info: PickingInfoLike) => onSelectArticle(info.object?.article_id ?? null),

        updateTriggers: {
          getRadius: [visualMode, selectedArticleId, hoveredArticleId, neighborKey, hasActiveMatch, JSON.stringify(activeMatchTarget)],
          getFillColor: [visualMode, colorMode, selectedArticleId, hoveredArticleId, neighborKey, hasSelection, hasActiveMatch, JSON.stringify(activeMatchTarget)],
          getLineColor: [visualMode, selectedArticleId, hoveredArticleId, neighborKey, hasSelection, hasActiveMatch, JSON.stringify(activeMatchTarget)],
          getLineWidth: [visualMode, selectedArticleId, hoveredArticleId, neighborKey, hasSelection, hasActiveMatch, JSON.stringify(activeMatchTarget)],
        },
      }),
    ]
  }, [points, visibleItems, viewMode, visualMode, colorMode, activeMatchTarget, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle, hasSelection, hasActiveMatch])

  const activeViewState = viewState[viewMode]

  return (
    <div className="map-frame">
      {/* Initial load overlay */}
      {loading && !points && (
        <div className="map-loading-overlay">
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            Loading semantic projection…
          </div>
        </div>
      )}

      <div
        ref={canvasRef}
        className={`map-canvas${loading && points ? ' loading-update' : ''}`}
      >
        {/* BUG-2 fix: key="explorer-deck" prevents StrictMode double-mount identity loss.
            BUG-4 fix: OrthographicView/OrbitView with no id (unnamed single-view mode);
                       viewState is passed as a plain object — DeckGL handles it correctly. */}
        <DeckGL
          key="explorer-deck"
          views={viewMode === '3d' ? [new OrbitView()] : [new OrthographicView()]}
          controller={
            viewMode === '3d'
              ? { dragMode: 'rotate', inertia: true }
              : { dragRotate: false, doubleClickZoom: true, touchRotate: false }
          }
          layers={layers}
          viewState={activeViewState as never}
          onViewStateChange={({ viewState: nextViewState }) => {
            setViewState((current) => ({
              ...current,
              [viewMode]: nextViewState as ViewStateMap[typeof viewMode],
            }))
          }}
        >
          {error && (
            <div className="map-empty-state">
              <strong>Failed to load semantic projection</strong>
              <p>{error}</p>
            </div>
          )}
          {!loading && !error && visibleItems.length === 0 && (
            <div className="map-empty-state">
              <strong>No articles match the current filters</strong>
              <p>
                {editorialTarget
                  ? `No visible points match article type ${editorialTarget.value.replace(/_/g, ' ')}. Clear the lens, switch back to highlight mode, or broaden the base subset.`
                  : 'Broaden the source or date scope, clear the cluster filter, or switch back to highlight mode.'}
              </p>
            </div>
          )}
          {tooltip && (
            <Tooltip
              tooltip={tooltip}
              canvasWidth={canvasRef.current?.clientWidth ?? 9999}
              canvasHeight={canvasRef.current?.clientHeight ?? 9999}
            />
          )}
        </DeckGL>

        {/* Dev diagnostic overlay — stripped in production builds */}
        {import.meta.env.DEV && (
          <DevDiagnostic
            points={points}
            activeViewState={activeViewState}
            canvasEl={canvasRef.current}
          />
        )}
      </div>
    </div>
  )
})

// ─── Tooltip ─────────────────────────────────────────────────────────────────

const TOOLTIP_WIDTH = 288  // max-width: 18rem ≈ 288px
const TOOLTIP_HEIGHT = 120 // approximate

function Tooltip({
  tooltip,
  canvasWidth,
  canvasHeight,
}: {
  tooltip: NonNullable<TooltipState>
  canvasWidth: number
  canvasHeight: number
}) {
  const point = tooltip.point
  // Clamp tooltip so it doesn't overflow canvas edges
  const left = Math.min(tooltip.x + 14, canvasWidth - TOOLTIP_WIDTH - 8)
  const top = Math.min(tooltip.y + 14, canvasHeight - TOOLTIP_HEIGHT - 8)

  return (
    <div className="tooltip-card" style={{ left, top }}>
      <div className="tooltip-eyebrow">
        <span>{point.source}{point.section ? ` · ${point.section}` : ''}</span>
        {point.analysis.is_outlier && (
          <span className="tooltip-outlier-badge">Outlier</span>
        )}
      </div>
      <strong>{point.title}</strong>
      <div className="tooltip-meta">{formatDate(point.published_at)}</div>
      <div className="tooltip-cluster-meta">
        {point.analysis.cluster_id != null
          ? `Cluster ${point.analysis.cluster_id}`
          : 'No cluster'}
      </div>
      <div className="tooltip-cluster-meta">{describeEditorialPreview(point.editorial_preview)}</div>
      {point.summary_snippet && <p>{point.summary_snippet}</p>}
    </div>
  )
}

// ─── Dev diagnostic overlay ───────────────────────────────────────────────────

function DevDiagnostic({
  points,
  activeViewState,
  canvasEl,
}: {
  points: ExplorerPointsResponse | null
  activeViewState: { zoom: number; target: [number, number, number] }
  canvasEl: HTMLDivElement | null
}) {
  const b = points?.meta.bounds
  const boundsStr = b
    ? `[${b.min_x.toFixed(2)},${b.max_x.toFixed(2)},${b.min_y.toFixed(2)},${b.max_y.toFixed(2)}]`
    : 'null'

  return (
    <div className="map-debug-overlay">
      {`pts:${points?.items.length ?? 0} | canvas:${canvasEl?.clientWidth ?? '?'}×${canvasEl?.clientHeight ?? '?'} | zoom:${activeViewState.zoom.toFixed(2)} | bounds:${boundsStr}`}
    </div>
  )
}
