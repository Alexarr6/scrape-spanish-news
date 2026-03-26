# RESULTS.md — iter/011 frontend.react pass

## Resumen breve

Este iter arregla el problema real sin inventarse backend nuevo:
- **Breaking Event, Coverage y Editorial Lens** ahora usan el mismo contrato estructural de sección mayor
- **Editorial Lens** dejó de ser una feria de métricas flojas y pasó a un bloque compacto, centrado en fuente
- **Nearby Articles** salió del detalle inline del artículo y vive como sección propia justo debajo de Editorial Lens
- el resto del drill-in de artículo quedó estable salvo esa extracción deliberada

## Qué cambió

### 1. Shell compartido para las secciones mayores
En `frontend/src/components/stories/StoryFocusPanel.tsx` y `frontend/src/styles.css`:
- añadí un patrón común `story-focus-major-section` + `story-focus-major-shell`
- lo apliqué a:
  - `Breaking event`
  - `Coverage`
  - `Editorial lens`
  - y también al bloque nuevo de `Nearby articles`
- con eso desaparece la sensación de que cada sección viene de un planeta distinto

### 2. Simplificación fuerte de Editorial Lens
En `frontend/src/components/stories/EditorialLensSection.tsx`:
- eliminé del surface principal:
  - coverage grids superiores de applicability/article type
  - comparative metric index grid por fuente
  - metric notes
  - divergence callouts
  - cluster signals block
  - confidence/scope callouts sobredimensionados
- dejé sólo lo que sí aporta:
  - título + intro breve
  - badges de analyzed/pending/failed
  - fallback corto cuando la señal comparativa es floja
  - lista compacta por fuente
- cada fila de fuente ahora muestra:
  - nombre de fuente
  - analyzed / total (+ usable si existe)
  - badges de review relevantes
  - comparison note si existe
  - un resumen compacto con `Type mix` + `Editorial mix`
  - framing chips sólo si de verdad hay soporte

### 3. Nearby Articles movido a su propia sección
En `StoryFocusPanel.tsx`:
- añadí `NearbyArticlesSection` bajo Editorial Lens
- sigue usando exactamente `article.neighbors` del artículo seleccionado
- sólo aparece cuando hay artículo seleccionado y vecinos disponibles
- eliminé el bloque inline de nearby articles dentro de `ArticleDetailSection`

## Verificación ejecutada

```bash
cd frontend && npm run build
```

Resultado:
- build **OK**
- Vite emitió el warning ya existente de chunk grande, pero la compilación terminó correctamente

## Archivos tocados

Código/UI:
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/components/stories/EditorialLensSection.tsx`
- `frontend/src/styles.css`

Artefactos de iteración:
- `RESULTS.md`
- `STATUS.md`
- `logs/iterations/011.md`

## Git / disciplina

Implementación acotada al frontend Stories detail.
Sin cambios de backend ni de contratos de datos.
Commit atómico realizado para el pass de implementación.

## Veredicto honesto

La versión anterior enseñaba demasiada fontanería medio vacía. Esta queda bastante más limpia y coherente: Editorial Lens vuelve a contar algo útil, Nearby Articles deja de estorbar dentro del detalle, y la cabecera analítica por fin se alinea como un producto serio en vez de un collage.