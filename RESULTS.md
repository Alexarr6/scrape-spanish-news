# RESULTS.md

## Resumen de entrega

Se añadió una capa operativa en la raíz del repo: `Makefile` como interfaz canónica, detección automática del app runnable y un scheduler shell simple con `flock`, retry, logs y estado en `var/`.

## Cambios realizados
- `Makefile` en raíz con targets de preflight, test, smoke, run manual, persistencia, API, scheduler y verificaciones.
- `scripts/detect_app_root.sh` para preferir una futura app en raíz y, mientras tanto, caer al mejor `runs/*` runnable sin convertirlo en arquitectura oficial.
- `scripts/run_scheduled.sh` como entrypoint único para cron/systemd.
- `.gitignore` para ignorar `var/` runtime state.
- `README.md` y `STATUS.md` actualizados con el flujo root-first.

## Evidencias de verificación
- Pendiente ejecutar verificación final manual tras crear los archivos operativos.

## Pendientes / limitaciones
- El código runnable real todavía vive bajo `runs/...`; esto ahora está encapsulado por detección, no resuelto por refactor.
- `DATABASE_URL` sigue siendo obligatorio para `run-all-persist`, `api` y scheduler productivo.

## Recomendaciones siguientes
- Ejecutar `make preflight && make test`.
- Probar `make smoke SOURCE=elpais`.
- Con `DATABASE_URL`, probar `make scheduler-dry-run && make scheduler-once`.
- Si todo va fino, instalar cron fuera del repo.
