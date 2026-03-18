# RESULTS.md

## Resumen de entrega
Implementé la fase aprobada del semantic explorer sin abrir un circo nuevo. Ahora existe una base dual-view real: el backend genera y sirve `x/y/z`, el explorer puede alternar entre vista 2D y 3D en deck.gl, la 2D se lee bastante mejor, y la UI quedó más limpia sin meterse en un rediseño de producto.

## Cambios realizados

### Backend / pipeline semántico
- `src/semantic/contracts.py`
  - `PointArtifact` ahora modela `z` explícito.
- `src/semantic/project.py`
  - La proyección ya no está clavada a 2D.
  - `project_embeddings(..., dimensions=3)` genera PCA 3D real por defecto.
  - Los casos degenerados (1 o 2 filas / menos componentes disponibles) se rellenan de forma estable con ceros, sin NaN ni explosiones absurdas.
  - Se mantiene compatibilidad con 2D vía `dimensions=2`.
- `src/semantic/dbstore.py`
  - El projection set canónico del explorer pasa a `pca_3d_latest` con kind `pca_3d`.
  - Añadí `projection_kind_for_set()` para no mezclar sets 2D y 3D como si fueran lo mismo.
  - `refresh_projection_set()` persiste `z` real y resuelve si debe recalcular 2D o 3D según el set solicitado.
  - `load_projected_points()`, `load_explorer_points_page()` y `load_explorer_article_detail()` ya cargan `z`.
  - `_load_projection_bounds()` ahora devuelve bounds 3D (`min_z/max_z`).
  - Se conserva convivencia con `pca_2d_*` cuando se pidan esos sets.
- `src/api/contracts/semantic.py`
  - `ExplorerPoint` expone `z`.
  - `ExplorerProjectionBounds` expone `min_z/max_z`.
- `scripts/semantic_project.py`
  - Copy actualizado para dejar de vender la regeneración como solo 2D.
- `scripts/build_semantic_map.py`
  - `metrics.projection_method` ya refleja el kind real del projection set usado.

### Frontend / explorer
- `frontend/src/lib/types.ts`
  - Tipos actualizados para `z`, bounds 3D y modo de vista.
- `frontend/src/components/MapPanel.tsx`
  - Añadí alternancia explícita 2D/3D.
  - 2D usa `OrthographicView`; 3D usa `OrbitView`.
  - 2D renderiza `[x, y]`; 3D renderiza `[x, y, z]` reales.
  - Hay `Reset view` con cámara inicial razonable para ambos modos.
  - Se mantienen hover, tooltip, click/select e inspector.
  - Ajusté radius/opacidad/contorno para una nube 2D bastante más legible.
  - Añadí hints de uso mínimos para que la vista 3D no entre dando hostias al usuario.
- `frontend/src/routes/ExplorerPage.tsx`
  - Estado de modo de vista integrado en la shell del explorer.
- `frontend/src/components/StatusBar.tsx`
  - Copy y chips actualizados para reflejar dual-view real.
- `frontend/src/components/InspectorPanel.tsx`
  - El inspector muestra coordenadas `x, y, z` del punto seleccionado.
- `frontend/src/components/FilterBar.tsx`
  - Copy ajustado para mantener límites de scope honestos.
- `frontend/src/styles.css`
  - Pulido moderado de overlays, controles segmentados, hints y presentación general.

### Tests
- `tests/test_semantic_projection.py`
  - Cobertura para PCA 3D, datasets pequeños y compatibilidad 2D.
- `tests/test_semantic_contracts.py`
  - Verificación del nuevo campo `z` en artifacts.
- `tests/test_semantic_dbstore.py`
  - Cobertura para resolución de projection kind 2D/3D y ajuste del fake bounds 3D.
- `tests/test_api_semantic_explorer.py`
  - Contratos API actualizados para `pca_3d_latest`, `z` y bounds 3D.

## Verificación ejecutada
```bash
~/.local/bin/uv run pytest -q \
  tests/test_semantic_projection.py \
  tests/test_semantic_contracts.py \
  tests/test_semantic_dbstore.py \
  tests/test_api_semantic_explorer.py
```
- Resultado: `26 passed`

```bash
cd frontend && npm run build
```
- Resultado: build OK
- Observaciones:
  - sigue apareciendo un warning de chunk grande de Vite
  - aparece también un warning de `@loaders.gl` / `__vite-browser-external`
  - ninguno rompe el build en esta fase

## Commits atómicos creados
1. `62735ee` — `Add 3D projection artifacts and semantic explorer API support`
2. `5d9cf6e` — `Add dual 2D/3D explorer views with bounded UI polish`

## Caveats
- No ejecuté smoke manual completo con API viva + frontend + Postgres persistente porque en esta sesión no había un `DATABASE_URL` operativo ni un dataset materializado para hacerlo sin inventarme el entorno.
- El explorer ahora asume como default `pca_3d_latest`; si el entorno real solo tiene el set 2D viejo, primero hay que materializar el 3D:
```bash
make semantic-project PROJECTION_SET=pca_3d_latest
```

## Estado funcional esperado
- El explorer carga un projection set 3D explícito y separado del 2D.
- Los puntos exponen y consumen `x/y/z` reales end-to-end.
- La UI permite alternar entre 2D y 3D sin romper hover, click/select ni inspector.
- La vista 2D deja de verse tan apelmazada por framing y styling básicos mal calibrados.
- La vista 3D tiene navegación mínima usable con orbit, zoom, pan y reset.
