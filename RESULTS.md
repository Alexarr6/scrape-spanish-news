# RESULTS.md — iter/020 lot 4B docs/operator contract alignment

## Resumen breve

Iter/020 hizo la limpieza mínima aprobada del **lot 4B** del `TECH_DEBT_AUDIT.md`.

Se tocaron solo las superficies docs/operator aprobadas para alinear el contrato con la superficie canónica real:
- `docs/operator-guide/workflows.md`
- `docs/reference/outputs.md`

No hubo cambios de código, no hubo cambios de `Makefile` y no se vendió la ruta legacy como si hubiera desaparecido mágicamente.

## Qué se hizo

- se reescribió la sección de scheduler en `docs/operator-guide/workflows.md` para que el flujo principal apunte a:
  - `bash scripts/run_stories_refresh.sh`
  - `bash scripts/run_explorer_refresh.sh`
  - `make full-refresh-once`
- se documentó el split activo Stories + Explorer con su cron shape recomendada
- se mantuvo `bash scripts/run_scheduled.sh` documentado como wrapper legacy scrape-only, dejando claro que sigue existiendo pero ya no es la entrada canónica del producto principal
- se actualizó `docs/reference/outputs.md` para reflejar el layout activo por job:
  - `var/lock/stories-refresh.lock`
  - `var/lock/explorer-refresh.lock`
  - `var/log/stories-refresh.log`
  - `var/log/explorer-refresh.log`
  - `var/state/stories_*`
  - `var/state/explorer_*`
- se conservaron y documentaron honestamente los ficheros legacy del scheduler scrape-only:
  - `var/log/scheduler.log`
  - `var/state/last_*`
  - `var/state/consecutive_failures`
  - `var/state/last_alert_utc`

## Verificación ejecutada

1. `make docs-build`

## Resultado de verificación

- `make docs-build` pasó con **exit 0**
- MkDocs construyó el sitio correctamente
- siguieron apareciendo avisos no bloqueantes sobre páginas existentes fuera de `nav`; son ruido conocido del repo, no un fallo introducido por este lote

## Notas

- alcance mantenido estrecho de verdad: solo alineación del contrato docs/operator
- no hizo falta tocar `docs/operator-guide/scheduler.md` ni `README.md`
- el wording legacy quedó honesto: sigue ahí, sigue siendo runnable, pero no vuelve a ocupar el trono por accidente

## Veredicto

Cambio pequeño, correcto y sin teatro: las docs dejan de contar dos historias distintas sobre el scheduler y la referencia de outputs ya refleja el layout activo real.