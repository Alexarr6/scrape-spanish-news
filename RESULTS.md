# RESULTS.md — iter/025 frontend navigation / URL-state refactor phase 1

## Resumen breve

Iter/025 ejecutó la fase 1 aprobada del refactor de navegación/URL-state del frontend sin meterse en la estupidez de medio reescribir el router.

`App.tsx` pasó a ser el dueño explícito del modo de la app (`stories` vs `explorer`) para **render** y **nav active state**. Además, se extrajeron helpers mínimos de mecánica URL compartida y `navigation.ts` quedó reducido a builders de handoff explícitos entre superficies.

Stories y Explorer siguen siendo dominios de estado separados. No se creó ningún mega-hook genérico.

## Cambio aplicado

### App shell
- `frontend/src/App.tsx`
  - resuelve `appMode` una sola vez con `getAppModeFromSearch()`
  - construye los `navItems` dentro del componente, no congelados a nivel de módulo
  - usa el mismo `appMode` tanto para el item activo de navegación como para decidir si renderiza `ClusterBrowserPage` o `ExplorerPage`

### Helpers compartidos
- `frontend/src/lib/urlState.ts` (nuevo)
  - lectura/clonado de `URLSearchParams`
  - borrado de listas conocidas de params
  - serialización/reemplazo de URL preservando `pathname` y `hash`
  - parseo genérico de enteros positivos / no negativos / opcionales
  - helper mínimo de modo de app (`getAppModeFromSearch`, `buildAppModeHref`)

### Hooks de URL-state
- `frontend/src/hooks/useClusterUrlState.ts`
  - conserva la propiedad del dominio Stories (`search`, `source`, `tag`, `entity`, `from`, `to`, `limit`, `offset`, `cluster`, `article`)
  - elimina parse helpers duplicados
  - reutiliza helpers compartidos para leer/borrar/escribir params

- `frontend/src/hooks/useExplorerUrlState.ts`
  - conserva la propiedad del dominio Explorer (`view=semantic`, `sem_*`, visual/editorial state)
  - elimina parse helpers duplicados
  - reutiliza helpers compartidos para leer/borrar/escribir params

### Handoff explícito entre superficies
- `frontend/src/lib/navigation.ts`
  - elimina la lectura ambiental de modo de app
  - sustituye builders vagos por:
    - `buildStoriesSurfaceHref(...)`
    - `buildExplorerSurfaceHref(...)`
  - `buildExplorerSurfaceHref(...)` mantiene el contrato de seeded transition:
    - fuerza `view=semantic`
    - si hay contexto, siembra `sem_story_cluster` y/o `sem_article`
    - fuerza `sem_mode=highlight`
    - fuerza `sem_color=active-match`
    - limpia sólo los filtros Explorer incompatibles declarados (`sem_search`, `sem_source`, `sem_from`, `sem_to`, `sem_cluster`, `sem_section`, `sem_outliers`, `sem_editorial_dim`, `sem_editorial_value`)

### Call sites ajustados
- `frontend/src/components/stories/StoryFocusPanel.tsx`
  - usa el nuevo builder explícito hacia Explorer para el empty state y para los CTAs de “Open in Explorer”

## Invariantes preservadas

- Stories sigue siendo el modo por defecto cuando no existe `view=semantic`
- Explorer sigue activándose sólo cuando `view=semantic` está presente
- Los deep links de Stories y Explorer sobreviven porque cada hook sigue leyendo sólo sus claves
- Las transiciones Stories → Explorer siguen sembrando contexto de story/article y defaults visuales esperados
- No hubo rediseño visual amplio ni router rewrite

## Verificación ejecutada

1. revisión de diff contra la arquitectura aprobada
2. `cd frontend && npm run build`

## Resultado de verificación

- `npm run build`: **ok**
- Vite emitió warnings preexistentes/no bloqueantes:
  - warning de chunk grande >500 kB
  - warning de `@loaders.gl/worker-utils` / `spawn` durante build, pero la build completó correctamente

## Commits

- `de62251` — `refactor(frontend): centralize app mode and url mechanics`

## Riesgo residual honesto

Quedan deudas de routing más profundas fuera de esta fase: no hay sincronización dedicada de `popstate`, no se renombró el esquema de params y no existe routing por paths. Bien. Eso era justo lo que había que **no** hacer aquí.
