# RESULTS.md

## Resumen de entrega

La raíz del repo quedó como única estructura canónica. `src/`, `tests/`, scripts y fixtures viven en ubicaciones estables y `runs/` fue eliminado por completo después de mover lo útil a `tests/fixtures/evidence/20260314-1212-8ff9/`.

## Cambios realizados
- `Makefile` corregido en `verify-output`: las rutas ahora usan `$${source}` para evitar la expansión rota tipo `source_2026` cuando `DATE` empieza por año y Bash corre con `set -u`.
- `scripts/run_scheduled.sh` endurecido: cada paso de `run_attempt()` devuelve fallo explícitamente (`|| return $?`) para que `scheduler-once` no marque éxito si `verify-output` o `verify-db` revientan.
- `src/` promovido a raíz como código canónico.
- `tests/` promovido a raíz como suite canónica.
- `docs/contracts/comparison_summary.schema.json` promovido a raíz.
- `scripts/generate_comparison_summary.py` promovido a `scripts/`.
- `pyproject.toml` actualizado para describir la app real, añadir `psycopg[binary]` y ahora también `httpx` en dev para tests de FastAPI.
- `src/persistence/db.py` actualizado para normalizar URLs PostgreSQL hacia `postgresql+psycopg://`.
- `src/persistence/crud.py` endurecido: `ingest_many()` hace un solo commit por lote, `upsert()` reutiliza flush/refresh sin commits forzados por fila, y el fallo SQLAlchemy en lote provoca rollback total explícito.
- `src/persistence/contracts.py` amplía `IngestResult` con `rolled_back` para dejar clara la semántica de lote.
- Añadidos `tests/test_persistence_crud.py` y `tests/test_api_articles.py` con cobertura DB-backed para insert/update/idempotencia/rollback y rutas 200/404/422 con overrides de dependencia.
- `Makefile` y `scripts/run_scheduled.sh` simplificados para usar la raíz como único app root.
- `README.md`, `.gitignore` y `STATUS.md` actualizados al flujo root-first real y a la nueva semántica de persistencia.
- tests de evidencia adaptados para leer fixtures promovidos a `tests/fixtures/evidence/20260314-1212-8ff9/`, sin depender de un árbol archivado vivo.
- `tests/test_export_article_text.py` ya no escribe salidas temporales dentro de `runs/...`; usa un directorio temporal aislado.
- Se añadió `pre-commit` con solo hooks de Ruff (`ruff-check`, `ruff-format`) y un `make check` canónico para el gate local.
- Se eliminó el shim legado `scripts/detect_app_root.sh`, se limpiaron caches/artefactos obvios del repo y se borró `runs/` tras retirar sus últimas dependencias.

## Validación intentada
- `make verify-output DATE=2026-03-15 OUT_PREFIX=sched SOURCE=source_2026` antes del fix reproducía el fallo real: `bash: line 5: source_2026: unbound variable` ✅
- `make verify-output DATE=2026-03-15 OUT_PREFIX=sched SOURCE=source_2026` después del fix ya no intenta expandir `source_2026`; falla honestamente por ficheros ausentes (`missing ...`) ✅
- `DATABASE_URL='postgresql+psycopg://dummy:dummy@127.0.0.1:5432/dummy' SCHEDULER_MAX_RETRIES=0 bash scripts/run_scheduled.sh` ahora devuelve exit code 2 y escribe estado `failed` / `scheduled run failed after 1 attempt(s) ...` cuando `verify-output` falla ✅
- `make check` ❌ en este host por problemas previos no relacionados: árbol sucio y un test de scraper (`tests/test_sources.py::test_scrape_elpais_produces_articles`) sigue fallando.
- El path de DB local con Docker Compose sigue siendo opcional y dependiente del host.

## Caveats
- Los nuevos tests de persistencia/API usan SQLite aislado para estabilidad local; no sustituyen una pasada de integración real contra Postgres.
- Los fixtures activos siguen usando el identificador histórico `20260314-1212-8ff9` para trazabilidad, pero ya viven bajo `tests/fixtures/evidence/...`.
- La validación Postgres local depende de que el host tenga Docker/Compose operativos.
