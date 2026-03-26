export type AppMode = 'stories' | 'explorer'

export function readSearchParams(search = window.location.search): URLSearchParams {
  return new URLSearchParams(search)
}

export function deleteSearchParams(params: URLSearchParams, keys: readonly string[]): URLSearchParams {
  for (const key of keys) params.delete(key)
  return params
}

export function buildHrefFromSearchParams(params: URLSearchParams): string {
  const text = params.toString()
  return `${window.location.pathname}${text ? `?${text}` : ''}${window.location.hash}`
}

export function replaceUrlSearchParams(params: URLSearchParams): void {
  window.history.replaceState(null, '', buildHrefFromSearchParams(params))
}

export function parseStrictPositiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

export function parseNonNegativeInt(value: string | null, fallback: number): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback
}

export function parseOptionalPositiveInt(value: string | null): number | null {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function getAppModeFromSearch(search = window.location.search): AppMode {
  return readSearchParams(search).get('view') === 'semantic' ? 'explorer' : 'stories'
}

export function isExplorerAppMode(search = window.location.search): boolean {
  return getAppModeFromSearch(search) === 'explorer'
}

export function buildAppModeHref(mode: AppMode): string {
  const params = readSearchParams()
  if (mode === 'explorer') params.set('view', 'semantic')
  else params.delete('view')
  return buildHrefFromSearchParams(params)
}
