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

export const BIAS_COLOR_HEX: Record<string, string> = {
  left: '#2563eb',
  center_left: '#0ea5e9',
  center: '#64748b',
  center_right: '#f59e0b',
  right: '#dc2626',
  mixed: '#7c3aed',
  unclear: '#94a3b8',
}

const ARTICLE_TYPE_COLOR_RGB: Record<string, [number, number, number]> = Object.fromEntries(
  Object.entries(ARTICLE_TYPE_COLOR_HEX).map(([label, hex]) => [label, hexToRgb(hex)]),
) as Record<string, [number, number, number]>

const BIAS_COLOR_RGB: Record<string, [number, number, number]> = Object.fromEntries(
  Object.entries(BIAS_COLOR_HEX).map(([label, hex]) => [label, hexToRgb(hex)]),
) as Record<string, [number, number, number]>

export const EDITORIAL_DIAGNOSTIC_COLOR_HEX = {
  pending: '#cbd5e1',
  failed: '#b45309',
  unknown: '#94a3b8',
  low_confidence: '#c08457',
  limited: '#64748b',
  out_of_domain: '#475569',
} as const

export function articleTypeColorRgb(label: string | null | undefined): [number, number, number] {
  if (!label) return ARTICLE_TYPE_COLOR_RGB.unclear
  return ARTICLE_TYPE_COLOR_RGB[label] ?? ARTICLE_TYPE_COLOR_RGB.unclear
}

export function biasColorRgb(label: string | null | undefined): [number, number, number] {
  if (!label) return BIAS_COLOR_RGB.unclear
  return BIAS_COLOR_RGB[label] ?? BIAS_COLOR_RGB.unclear
}

export function articleTypeColorForPreviewRgb(
  preview: ExplorerPointEditorialPreview | null | undefined,
): [number, number, number] {
  const bucket = getArticleTypeStatusBucket(preview)
  if (bucket === 'pending') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.pending)
  if (bucket === 'failed') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.failed)
  if (bucket === 'unknown') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.unknown)
  if (bucket === 'out_of_domain') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.out_of_domain)
  const base = articleTypeColorRgb(preview?.article_type)
  if (bucket === 'limited') {
    return mixRgb(base, hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.limited), 0.35)
  }
  return base
}

export function biasColorForPreviewRgb(
  preview: ExplorerPointEditorialPreview | null | undefined,
): [number, number, number] {
  const bucket = getBiasStatusBucket(preview)
  if (bucket === 'pending') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.pending)
  if (bucket === 'failed') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.failed)
  if (bucket === 'unknown') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.unknown)
  if (bucket === 'low_confidence') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.low_confidence)
  if (bucket === 'limited') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.limited)
  if (bucket === 'out_of_domain') return hexToRgb(EDITORIAL_DIAGNOSTIC_COLOR_HEX.out_of_domain)
  return biasColorRgb(preview?.bias_label)
}

export function humanizeArticleType(value: string | null | undefined) {
  return humanizeValue(value, 'Unknown')
}

export function humanizeBiasLabel(value: string | null | undefined) {
  return humanizeValue(value, 'Unknown')
}

export function humanizeEditorialDimension(value: ExplorerEditorialDimension | '' | null | undefined) {
  if (value === 'bias_label') return 'Bias'
  return 'Article type'
}

export function isEditorialValueMatch(
  point: ExplorerPoint,
  target: { dimension: ExplorerEditorialDimension; value: string } | null,
): boolean {
  if (!target) return false
  if (target.dimension === 'article_type') {
    return (point.editorial_preview?.article_type ?? 'unclear') === target.value
  }
  return isStrictBiasMatch(point.editorial_preview, target.value)
}

export function isStrictBiasMatch(
  preview: ExplorerPointEditorialPreview | null | undefined,
  targetValue: string,
): boolean {
  if (!preview) return false
  if (preview.analysis_status !== 'completed') return false
  if (preview.editorial_applicability !== 'full') return false
  if ((preview.bias_label ?? 'unclear') !== targetValue) return false
  if ((preview.bias_label ?? 'unclear') === 'unclear') return false
  if (preview.review_flags.low_confidence) return false
  if (preview.review_flags.unclear_bias) return false
  if (preview.review_flags.out_of_domain) return false
  return true
}

export function getArticleTypeStatusBucket(preview: ExplorerPointEditorialPreview | null | undefined) {
  if (!preview) return 'pending' as const
  if (preview.analysis_status === 'pending' || preview.review_flags.pending_analysis) return 'pending' as const
  if (preview.analysis_status === 'failed' || preview.review_flags.failed_analysis) return 'failed' as const
  if (!preview.article_type || preview.article_type === 'unclear') return 'unknown' as const
  if (preview.editorial_applicability === 'out_of_domain' || preview.review_flags.out_of_domain) return 'out_of_domain' as const
  if (preview.editorial_applicability === 'limited') return 'limited' as const
  return 'typed' as const
}

export function getBiasStatusBucket(preview: ExplorerPointEditorialPreview | null | undefined) {
  if (!preview) return 'pending' as const
  if (preview.analysis_status === 'pending' || preview.review_flags.pending_analysis) return 'pending' as const
  if (preview.analysis_status === 'failed' || preview.review_flags.failed_analysis) return 'failed' as const
  if (preview.editorial_applicability === 'out_of_domain' || preview.review_flags.out_of_domain) return 'out_of_domain' as const
  if (preview.editorial_applicability === 'limited') return 'limited' as const
  if (!preview.bias_label || preview.bias_label === 'unclear' || preview.review_flags.unclear_bias) return 'unknown' as const
  if (preview.review_flags.low_confidence) return 'low_confidence' as const
  return 'typed' as const
}

export function describeEditorialPreview(preview: ExplorerPointEditorialPreview | null | undefined) {
  const articleTypeBucket = getArticleTypeStatusBucket(preview)
  const biasBucket = getBiasStatusBucket(preview)
  const articleTypeText = (() => {
    if (articleTypeBucket === 'pending') return 'Pending editorial analysis'
    if (articleTypeBucket === 'failed') return 'Editorial analysis failed'
    if (articleTypeBucket === 'out_of_domain') return 'Out of domain for editorial analysis'
    if (articleTypeBucket === 'unknown') return 'Unknown article type'
    if (articleTypeBucket === 'limited') return `${humanizeArticleType(preview?.article_type)} article · limited editorial scope`
    return `${humanizeArticleType(preview?.article_type)} article`
  })()

  const biasText = (() => {
    if (biasBucket === 'pending') return 'Bias pending'
    if (biasBucket === 'failed') return 'Bias analysis failed'
    if (biasBucket === 'out_of_domain') return 'Bias out of domain'
    if (biasBucket === 'limited') return 'Bias limited'
    if (biasBucket === 'unknown') return 'Bias unknown / unclear'
    if (biasBucket === 'low_confidence') return `Bias ${humanizeBiasLabel(preview?.bias_label)} · low confidence`
    return `Bias ${humanizeBiasLabel(preview?.bias_label)}`
  })()

  return `${articleTypeText} · ${biasText}`
}

export function buildArticleTypeOptions(editorial: ExplorerEditorialMetadata | null | undefined) {
  return (editorial?.article_type ?? []).map((option) => ({
    value: option.value,
    label: humanizeArticleType(option.value),
    count: option.count,
  }))
}

export function buildBiasOptions(editorial: ExplorerEditorialMetadata | null | undefined) {
  return (editorial?.bias_label ?? []).map((option) => ({
    value: option.value,
    label: humanizeBiasLabel(option.value),
    count: option.count,
  }))
}

export function getCoverageCount(editorial: ExplorerEditorialMetadata | null | undefined, key: string) {
  return editorial?.coverage?.[key] ?? 0
}

function mixRgb(
  left: [number, number, number],
  right: [number, number, number],
  rightWeight: number,
): [number, number, number] {
  const leftWeight = 1 - rightWeight
  return [
    Math.round(left[0] * leftWeight + right[0] * rightWeight),
    Math.round(left[1] * leftWeight + right[1] * rightWeight),
    Math.round(left[2] * leftWeight + right[2] * rightWeight),
  ]
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = hex.replace('#', '')
  const value = Number.parseInt(normalized, 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}
