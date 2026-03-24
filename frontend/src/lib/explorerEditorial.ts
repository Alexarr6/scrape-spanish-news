import { humanizeValue } from '../components/editorial/editorialFormat'
import type {
  ExplorerEditorialDimension,
  ExplorerEditorialMetadata,
  ExplorerPoint,
  ExplorerPointEditorialPreview,
} from './types'

export const ARTICLE_TYPE_COLOR_HEX: Record<string, string> = {
  news: '#2563eb',
  opinion: '#d97706',
  editorial: '#dc2626',
  analysis: '#7c3aed',
  interview: '#059669',
  review: '#db2777',
  feature: '#0891b2',
  live: '#4f46e5',
  unclear: '#94a3b8',
}

const ARTICLE_TYPE_COLOR_RGB: Record<string, [number, number, number]> = Object.fromEntries(
  Object.entries(ARTICLE_TYPE_COLOR_HEX).map(([label, hex]) => [label, hexToRgb(hex)]),
) as Record<string, [number, number, number]>

export const EDITORIAL_DIAGNOSTIC_COLOR_HEX = {
  pending: '#cbd5e1',
  failed: '#f59e0b',
  unknown: '#94a3b8',
  limited: '#64748b',
  out_of_domain: '#475569',
} as const

export function articleTypeColorRgb(label: string | null | undefined): [number, number, number] {
  if (!label) return ARTICLE_TYPE_COLOR_RGB.unclear
  return ARTICLE_TYPE_COLOR_RGB[label] ?? ARTICLE_TYPE_COLOR_RGB.unclear
}

export function humanizeArticleType(value: string | null | undefined) {
  return humanizeValue(value, 'Unknown')
}

export function isEditorialValueMatch(
  point: ExplorerPoint,
  target: { dimension: ExplorerEditorialDimension; value: string } | null,
): boolean {
  if (!target || target.dimension !== 'article_type') return false
  return (point.editorial_preview?.article_type ?? 'unclear') === target.value
}

export function getEditorialStatusBucket(preview: ExplorerPointEditorialPreview | null | undefined) {
  if (!preview) return 'pending' as const
  if (preview.analysis_status === 'pending' || preview.review_flags.pending_analysis) return 'pending' as const
  if (preview.analysis_status === 'failed' || preview.review_flags.failed_analysis) return 'failed' as const
  if (!preview.article_type || preview.article_type === 'unclear') return 'unknown' as const
  if (preview.editorial_applicability === 'out_of_domain' || preview.review_flags.out_of_domain) return 'out_of_domain' as const
  if (preview.editorial_applicability === 'limited') return 'limited' as const
  return 'typed' as const
}

export function describeEditorialPreview(preview: ExplorerPointEditorialPreview | null | undefined) {
  const bucket = getEditorialStatusBucket(preview)
  if (bucket === 'pending') return 'Pending editorial analysis'
  if (bucket === 'failed') return 'Editorial analysis failed'
  if (bucket === 'out_of_domain') return 'Out of domain for editorial analysis'
  if (bucket === 'unknown') return 'Unknown article type'
  if (bucket === 'limited') return `${humanizeArticleType(preview?.article_type)} · limited editorial scope`
  return humanizeArticleType(preview?.article_type)
}

export function buildArticleTypeOptions(editorial: ExplorerEditorialMetadata | null | undefined) {
  return (editorial?.article_type ?? []).map((option) => ({
    value: option.value,
    label: humanizeArticleType(option.value),
    count: option.count,
  }))
}

export function getCoverageCount(editorial: ExplorerEditorialMetadata | null | undefined, key: string) {
  return editorial?.coverage?.[key] ?? 0
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = hex.replace('#', '')
  const value = Number.parseInt(normalized, 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}
