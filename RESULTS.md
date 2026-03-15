# RESULTS.md

## Resumen de entrega

Se dejó la raíz del repo como superficie operativa canónica con workflow gestionado por `uv`: `pyproject.toml` real, `ruff` configurado, `Makefile` usando `uv run`, detección automática del app runnable y un scheduler shell simple con `flock`, retry, logs y estado en `var/`.

## Cambios realizados
- `pyproject.toml` en raíz con dependencias runtime/dev reales y configuración canónica de `ruff`.
- `.python-version` para fijar el runtime esperado.
- `Makefile` en raíz con targets de sync, preflight, lint, test, smoke, run manual, persistencia, API, scheduler y verificaciones, todo vía `uv`.
- nuevos targets opcionales de DB local: `db-url`, `db-up`, `db-down`, `db-logs`, `db-psql`, `db-check`.
- `compose.yaml` con un Postgres local mínimo para pruebas de persistencia end-to-end.
- `.env.example` con valores aburridos de desarrollo local, sin secretos reales.
- `scripts/detect_app_root.sh` para preferir una futura app en raíz y, mientras tanto, caer al mejor `runs/*` runnable sin convertirlo en arquitectura oficial.
- `scripts/run_scheduled.sh` como entrypoint único para cron/systemd.
- `.gitignore` para ignorar `var/` runtime state.
- `README.md` y `STATUS.md` actualizados con el flujo root-first y la verificación local con Postgres.

## Evidencias de verificación
- validación estática del `Makefile` y documentación completada.
- la verificación runtime de `db-up`/`db-check`/`scheduler-once` depende de que este host tenga Docker Compose y de aceptar tráfico saliente del scraper; si no, quedan documentados los comandos exactos para que el humano lo ejecute.

## Pendientes / limitaciones
- El código runnable real todavía vive bajo `runs/...`; esto ahora está encapsulado por detección, no resuelto por refactor.
- `DATABASE_URL` sigue siendo obligatorio para `run-all-persist`, `api` y scheduler productivo.

## Recomendaciones siguientes
- Ejecutar `make preflight && make test`.
- Probar `make smoke SOURCE=elpais`.
- Con `DATABASE_URL`, probar `make scheduler-dry-run && make scheduler-once`.
- Si todo va fino, instalar cron fuera del repo.
