/**
 * explorerColors.ts — Single authoritative source for all Explorer point
 * encoding constants.  Replaces inline magic color arrays in MapPanel.tsx.
 *
 * See DESIGN_TOKENS.md Section 12.2 for the full specification.
 */

// ─── Selected point ──────────────────────────────────────────────────────────
export const POINT_SELECTED_FILL: [number, number, number, number] = [14, 165, 233, 255]   // sky-500 full
export const POINT_SELECTED_STROKE: [number, number, number, number] = [255, 255, 255, 255] // white
export const POINT_SELECTED_STROKE_WIDTH = 2.8
export const POINT_SELECTED_RADIUS_2D = 9
export const POINT_SELECTED_RADIUS_3D = 10

// ─── Semantic neighbors ──────────────────────────────────────────────────────
export const POINT_NEIGHBOR_FILL: [number, number, number, number] = [34, 197, 94, 235]     // green-500
export const POINT_NEIGHBOR_STROKE: [number, number, number, number] = [220, 252, 231, 240]  // green-100
export const POINT_NEIGHBOR_STROKE_WIDTH = 1.5
export const POINT_NEIGHBOR_RADIUS_2D = 7
export const POINT_NEIGHBOR_RADIUS_3D = 7.5

// ─── Hovered (unselected) ────────────────────────────────────────────────────
export const POINT_HOVERED_FILL: [number, number, number, number] = [125, 211, 252, 235]    // sky-300
export const POINT_HOVERED_STROKE: [number, number, number, number] = [224, 242, 254, 235]  // sky-100
export const POINT_HOVERED_STROKE_WIDTH = 0.8
export const POINT_HOVERED_RADIUS_2D = 6
export const POINT_HOVERED_RADIUS_3D = 6.5

// ─── Regular and outlier points — alpha by selection state ───────────────────
export const POINT_REGULAR_ALPHA_NO_SELECTION = 210
export const POINT_REGULAR_ALPHA_UNDER_SELECTION = 65
export const POINT_OUTLIER_ALPHA_NO_SELECTION = 230
export const POINT_OUTLIER_ALPHA_UNDER_SELECTION = 100

export const POINT_REGULAR_RADIUS_2D = 4
export const POINT_REGULAR_RADIUS_3D = 4.5
export const POINT_OUTLIER_RADIUS_2D = 5.5
export const POINT_OUTLIER_RADIUS_3D = 6

// ─── Stroke for receding (under-selection) points — effectively invisible ────
export const POINT_RECEDING_STROKE: [number, number, number, number] = [226, 232, 240, 0]  // transparent
export const POINT_RECEDING_STROKE_WIDTH = 0

// ─── Stroke for visible regular points (no selection active) ─────────────────
export const POINT_DEFAULT_STROKE: [number, number, number, number] = [248, 250, 252, 190] // slate-50 semi
export const POINT_DEFAULT_STROKE_WIDTH = 0.6

// ─── Source color palette ────────────────────────────────────────────────────
/** RGB tuples for ScatterplotLayer getFillColor */
export const SOURCE_COLORS: Record<string, [number, number, number]> = {
  elpais:       [59, 130, 246],    // blue-500
  elmundo:      [16, 185, 129],    // emerald-500
  abc:          [249, 115, 22],    // orange-500
  eldiario:     [168, 85, 247],    // purple-500
  lavanguardia: [236, 72, 153],    // pink-500
  '20minutos':  [251, 191, 36],    // amber-400
} as const

export const SOURCE_FALLBACK_COLOR: [number, number, number] = [100, 116, 139]  // slate-500

/** Hex values for CSS swatch rendering in the legend */
export const SOURCE_COLORS_HEX: Record<string, string> = {
  elpais:       '#3b82f6',
  elmundo:      '#10b981',
  abc:          '#f97316',
  eldiario:     '#a855f7',
  lavanguardia: '#ec4899',
  '20minutos':  '#fbbf24',
} as const

// ─── Cluster color palette ───────────────────────────────────────────────────
export const CLUSTER_PALETTE: Array<[number, number, number]> = [
  [67, 56, 202],     // indigo-700
  [3, 105, 161],     // sky-700
  [4, 120, 87],      // emerald-700
  [180, 83, 9],      // amber-700
  [157, 23, 77],     // rose-800
  [109, 40, 217],    // violet-700
]

export const CLUSTER_OUTLIER_COLOR: [number, number, number] = [220, 38, 38]  // red-600
export const CLUSTER_NULL_COLOR: [number, number, number] = [148, 163, 184]   // slate-400
