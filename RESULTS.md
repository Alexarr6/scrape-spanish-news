# RESULTS.md

## Resumen de entrega
Se implementó iter/003 como una pasada de **productización del Explorer 3D**, sin volver a rediseñar el shell general. El foco estuvo donde debía: framing de cámara, controles más legibles, leyenda persistente, mejor énfasis visual durante selección, y una right rail con estructura útil en vez de una pila mezclada de cosas.

## Cambios realizados

### 1) Cámara / framing / focus
Archivos principales:
- `frontend/src/components/MapPanel.tsx`

Cambios:
- se reemplazó el framing simple por un cálculo más explícito de **fit-to-bounds con padding y suelo mínimo de span**
- el Explorer ahora **auto-fit** en carga inicial y cuando cambia el subset visible
- `Fit all` vuelve al framing calculado del dataset visible
- `Focus selected` ya no hace un salto bruto: centra y encuadra el artículo seleccionado usando también sus vecinos semánticos cuando existen
- en 3D se mantiene una órbita deliberada y estable, pero con zoom recalculado de forma más útil para nubes compactas

Resultado:
- datasets acotados cerca de `-1..1` dejan de abrir tan lejos
- la cámara se siente más intencional y menos genérica

### 2) Controles / leyenda / énfasis visual
Archivos principales:
- `frontend/src/components/MapPanel.tsx`
- `frontend/src/components/InspectorPanel.tsx`
- `frontend/src/styles.css`

Cambios:
- los controles superiores se reagruparon como **Projection / Color by / Frame**
- se añadió copy más explícito sobre **cuándo usar 2D vs 3D**
- se añadió guía inline persistente dentro del canvas
- el panel derecho sin selección ahora arranca con una **Guide + Legend** mucho más útil
- se mejoró el énfasis visual:
  - seleccionado = prioridad máxima
  - vecinos = prioridad secundaria clara
  - resto de puntos = atenuados cuando hay selección activa
  - outliers conservan identidad sin gritar demasiado

Resultado:
- el Explorer explica mejor qué está mostrando y para qué sirve
- la selección local ahora se lee bastante mejor dentro de nubes densas

### 3) Context panel y responsive cleanup
Archivos principales:
- `frontend/src/components/InspectorPanel.tsx`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/styles.css`

Cambios:
- el panel derecho pasó a tener tabs locales:
  - sin selección: `Guide`, `Legend`
  - con selección: `Article`, `Cluster`, `Legend`
- se separó claramente:
  - evidencia del artículo
  - contexto del cluster
  - referencia persistente de lectura
- el tab de cluster usa metadata ya disponible para dar contexto sin meter backend nuevo
- en responsive:
  - la barra de controles colapsa mejor
  - el Explorer pasa antes a layout más limpio en anchuras intermedias
  - el panel de contexto baja de fila antes de que todo se apelotone

Resultado:
- la right rail ahora tiene jerarquía real
- el Explorer se degrada bastante mejor en widths intermedios

## Verificación ejecutada
Comando mínimo requerido ejecutado varias veces durante la implementación y al final:

```bash
cd frontend && npm run build
```

Resultado final:
- PASS

Notas del build:
- sigue apareciendo el warning no bloqueante de `@loaders.gl/worker-utils` / browser external `spawn`
- sigue apareciendo el warning no bloqueante de chunk grande (~914 kB minificado)
- no hizo falta tocar backend ni estructuras API compartidas, así que no corrí `pytest`

## Pendientes / no resueltos
- hotfix posterior: el rediseño dejó el viewport del Explorer sin una altura explícita/flexible fiable (`.map-canvas` dependía de `min-height: 100%`), así que DeckGL podía quedarse con un canvas colapsado o invisiblemente pequeño pese a que el shell sí se veía
- fix aplicado en `frontend/src/styles.css`: `map-frame` ahora actúa como contenedor flex vertical y `map-canvas` recibe un viewport explícito (`flex: 1` + `min-height: 42rem`, con el hijo directo ocupando `height: 100%`)
- el warning de chunk grande sigue vivo; eso encaja bien como **iteración opcional de performance** con lazy-loading o code-splitting del Explorer
- el tab de cluster es útil, pero todavía es derivado de metadata existente; una iteración futura podría enriquecerlo con más narrativa o métricas específicas si de verdad aportan valor
- la experiencia visual ya es bastante más analítica, pero aún podría afinarse con una pasada de microcopy y validación manual sobre datasets especialmente raros o dispersos

## Commits atómicos creados
1. `52deeb6` — `feat(explorer): improve semantic camera fit and selection framing`
2. `dc6a254` — `feat(explorer): clarify controls legend and point emphasis`
3. latest HEAD on `iter/003` — `feat(explorer): reorganize side-panel context and responsive layout`

## Git summary
- branch: `iter/003`
- repo verified with:

```bash
git rev-parse --is-inside-work-tree
git branch --show-current
```

### Recent relevant commits
```bash
git log --oneline -n 6
```

### Rollback / review hint
Para revisar por fases:
- cámara / framing: `52deeb6`
- controles / leyenda / énfasis: `dc6a254`
- side-panel / responsive: usar el siguiente commit de esta iteración

Rollback razonable si hubiera que deshacer iter/003 completo:
- volver al commit inmediatamente anterior a `52deeb6`
