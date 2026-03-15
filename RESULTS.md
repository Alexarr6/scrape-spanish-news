# RESULTS.md

## Resumen de entrega

Se promovió la app canónica desde `runs/20260314-1212-8ff9/` a la raíz del repo. La raíz ya contiene `src/`, `tests/` y los assets mínimos necesarios para operar y testear. `runs/` queda como archivo/evidencia, no como dependencia de runtime.

## Cambios realizados
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
- tests de evidencia adaptados para leer fixtures promovidos a `tests/fixtures/evidence/20260314-1212-8ff9/`, sin depender del árbol archivado completo.
- Se añadió `pre-commit` con solo hooks de Ruff (`ruff-check`, `ruff-format`) y un `make check` canónico para el gate local.
- Se eliminó el shim legado `scripts/detect_app_root.sh` y se limpiaron caches/artefactos obvios del repo.

## Validación intentada
- `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_persistence_crud.py tests/test_api_articles.py` ✅
- `make check` ✅
- `make test` ✅
- El path de DB local con Docker Compose sigue siendo opcional y dependiente del host.

## Caveats
- Los nuevos tests de persistencia/API usan SQLite aislado para estabilidad local; no sustituyen una pasada de integración real contra Postgres.
- `runs/` sigue siendo archivo/evidencia; los tests ya no dependen de rutas vivas dentro de ese árbol para sus fixtures activas.
- No se borró ni reescribió historia bajo `runs/`.
