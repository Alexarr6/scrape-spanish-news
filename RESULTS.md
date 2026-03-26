# RESULTS.md — iter/012 frontend.react pass

## Resumen breve

Este iter termina de limpiar la parte baja de Stories sin tocar backend ni inventar contratos nuevos:
- **Articles by source** ahora usa el mismo shell de sección mayor que el resto del panel
- el drill-in de artículo quedó reducido a lo que sí aporta: **volver, contexto, titular, fecha, resumen, Open in Explorer y nearby articles**
- desaparecen de Stories los bloques medio-debug que sobraban: **Open article, EditorialAnalysisCard, cluster membership diagnostics y semantic context metrics**
- **Nearby articles** vuelve al drill-in del artículo seleccionado, que era donde tenía sentido para esta iteración

## Qué cambió

### 1. Alineación estructural real para `Articles by source`
En `frontend/src/components/stories/StoryFocusPanel.tsx`:
- moví `Articles by source` al mismo patrón `story-focus-major-section` + `story-focus-major-shell`
- el shell final ahora cambia limpiamente entre:
  - listado agrupado por fuente, o
  - detalle del artículo seleccionado
- eliminé el viejo camino con `SectionDivider` suelto + `.focus-section`, que era el parche feo que desalineaba la sección

En `frontend/src/styles.css`:
- añadí una variante ligera `story-focus-major-shell-final` para que el shell mayor dé el marco general sin crear una muñeca rusa de cards dentro de cards

### 2. Drill-in de artículo reducido a surface de producto
En `StoryFocusPanel.tsx`:
- `ArticleDetailSection` conserva sólo:
  - back affordance
  - source/section eyebrow
  - headline
  - published date
  - summary / excerpt fallback
  - `Open in Explorer`
  - nearby articles cuando existen vecinos
- eliminé por completo:
  - `Open article ↗`
  - `EditorialAnalysisCard`
  - `ClusterMembershipDiagnostics`
  - grid de métricas semánticas
  - helpers muertos como `MetricItem`

### 3. Nearby articles vuelve al flujo del artículo seleccionado
- quité la sección mayor independiente de `Nearby articles`
- ahora se renderiza dentro del detalle del artículo, debajo del resumen y CTA
- sólo aparece cuando `article.neighbors.length > 0`
- añadí un header ligero para ese bloque y mantuve el listado de vecinos estable

## Verificación ejecutada

```bash
cd frontend && npm run build
```

Resultado:
- build **OK**
- Vite siguió mostrando warnings ya existentes de bundle/chunk grande y un warning de `spawn` desde `@loaders.gl/worker-utils`, pero la compilación terminó correctamente

## Archivos tocados

Código/UI:
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/styles.css`

Artefactos de iteración:
- `RESULTS.md`
- `STATUS.md`
- `logs/iterations/012.md`

## Git / disciplina

Implementación acotada al frontend de Stories.
Sin cambios de backend ni de contratos de datos.
Commit atómico realizado para este pass de simplificación del lower detail.

## Veredicto honesto

Antes esta parte parecía un cruce raro entre producto y panel de fontanería. Ahora Stories vuelve a hacer su trabajo: comparar cobertura, abrir un artículo, darte lo esencial y mandarte a Explorer cuando quieras cavar más hondo. Mucho mejor. 
