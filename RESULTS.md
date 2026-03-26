# RESULTS.md — iter/014 frontend.react pass

## Resumen breve

Iter/014 corrige dos mini-regresiones visuales sin tocar nada más:
- Cluster Context deja de renderizar sus métricas con clases muertas `metric-*`
- las métricas ahora reutilizan el patrón existente `.editorial-dimension-*`
- las cards de artículos en Stories recuperan un rail izquierdo sutil por defecto, mientras la seleccionada sigue mandando con un acento más fuerte

## Qué cambió

### 1. Fix quirúrgico del bloque Cluster Context
En `frontend/src/components/explorer/ExplorerContextRail.tsx`:
- `MetricItem` ya no usa:
  - `metric-item`
  - `metric-label`
  - `metric-value`
- ahora usa:
  - `editorial-dimension-item`
  - `editorial-dimension-label`
  - `editorial-dimension-value`

Eso reaprovecha el contrato visual que ya existe en la app para label/value items y evita inventar CSS nueva para algo que ya estaba resuelto.

### 2. Restore del left rail por defecto en Stories
En `frontend/src/styles.css`:
- `.member-card` deja de tener `border-left` transparente
- ahora usa un left rail sutil con `var(--color-border-strong)`
- `.member-card.selected` sigue elevándolo con `var(--color-accent)`

Resultado: la lista vuelve a tener anclaje visual sin convertir cada card en un cartel luminoso.

## Verificación ejecutada

```bash
cd frontend && npm run build
```

Resultado:
- build **OK**

## Archivos tocados

Código/UI:
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/styles.css`

Artefactos de iteración:
- `RESULTS.md`
- `STATUS.md`
- `logs/iterations/014.md`

## Git / disciplina

Cambio frontend-only, mínimo y atómico.
Sin backend, sin contratos nuevos, sin rediseños colaterales.

## Veredicto honesto

Era exactamente lo que parecía: clases fantasma en un bloque y un left rail demasiado muerto en el otro. Ya no parece roto, que era el puto objetivo.
