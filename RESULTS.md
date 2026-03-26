# RESULTS.md — iter/024 legacy scrape-only scheduler family removal

## Resumen breve

Iter/024 eliminó por completo la familia legacy del scheduler scrape-only que seguía viva en el repo: se borró `scripts/run_scheduled.sh`, se quitó su wiring en `Makefile`, y se limpiaron las referencias explícitas pedidas en README y docs.

La superficie canónica moderna quedó intacta: `run_stories_refresh.sh`, `run_explorer_refresh.sh`, `make stories-refresh-once`, `make explorer-refresh-once`, y `make full-refresh-once`, junto con la documentación `stories_*` / `explorer_*` de lock/log/state.

## Cambio aplicado

### Eliminado
- `scripts/run_scheduled.sh`
- variable `SCHEDULER_SCRIPT` en `Makefile`
- targets `scheduler-dry-run`, `scheduler-once`, `status`, `tail-log`
- bloque legacy de ayuda en `make help`

### Actualizado
- `README.md`
  - eliminado el bloque del scheduler legacy
  - eliminada la referencia de entrypoint `bash scripts/run_scheduled.sh`
  - ajustada la sección para exponer sólo la superficie moderna
- `docs/operator-guide/scheduler.md`
  - eliminados entrypoints/targets legacy
  - eliminada la sección `Legacy wrapper`
  - eliminado `var/log/scheduler.log` del layout documentado
- `docs/operator-guide/workflows.md`
  - eliminada la sección `Legacy scrape-only wrapper`
- `docs/reference/outputs.md`
  - eliminada la sección completa del layout legacy `scheduler.log` / `var/state/last_*`

## Evidencia de seguridad en repo

### Comprobación de eliminación
La comprobación acotada sobre los archivos objetivo no devolvió referencias restantes a:
- `run_scheduled.sh`
- `SCHEDULER_SCRIPT`
- `scheduler-dry-run`
- `scheduler-once`
- `make status`
- `make tail-log`
- `scheduler.log`
- `var/state/last_status`
- `var/state/last_run_utc`
- `var/state/last_success_utc`
- `var/state/last_error`
- `var/state/consecutive_failures`
- `var/state/last_alert_utc`

### Comprobación de preservación
La comprobación de superficie moderna confirmó que siguen presentes y documentados:
- `bash scripts/run_stories_refresh.sh`
- `bash scripts/run_explorer_refresh.sh`
- `make stories-refresh-once`
- `make explorer-refresh-once`
- `make full-refresh-once`
- los archivos `stories_*` / `explorer_*` bajo `var/state/`

## Verificación ejecutada

1. grep acotado de referencias legacy eliminadas
2. grep acotado de referencias modernas preservadas
3. `make help`
4. `make test`
5. `make docs-build`

## Resultado de verificación

- grep legacy acotado: **limpio**
- grep moderno acotado: **ok**
- `make help`: **ok**
- `make docs-build`: **ok**
- `make test`: **falló por un problema de entorno/dependencias no relacionado con este cambio**
  - durante colección de tests API apareció `ModuleNotFoundError: No module named 'fastapi'`
  - y también `ModuleNotFoundError: No module named 'fastapi.datastructures'`

## Riesgo residual honesto

El cambio de esta iteración es deliberadamente rompedor para cualquiera que aún estuviera usando el wrapper legacy scrape-only. Dentro del alcance pedido, la eliminación quedó limpia.

Lo único feo del pase fue `make test`, pero el fallo no apunta a esta limpieza del scheduler; huele a entorno/instalación de dependencias de FastAPI, no a la superficie moderna que se preservó.