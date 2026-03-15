# RESULTS.md

## Resumen de entrega

La raíz del repo quedó como única estructura canónica. `src/`, `tests/`, scripts y fixtures viven en ubicaciones estables y `runs/` fue eliminado por completo después de mover lo útil a `tests/fixtures/evidence/20260314-1212-8ff9/`.

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
- tests de evidencia adaptados para leer fixtures promovidos a `tests/fixtures/evidence/20260314-1212-8ff9/`, sin depender de un árbol archivado vivo.
- `tests/test_export_article_text.py` ya no escribe salidas temporales dentro de `runs/...`; usa un directorio temporal aislado.
- Se añadió `pre-commit` con solo hooks de Ruff (`ruff-check`, `ruff-format`) y un `make check` canónico para el gate local.
- Se eliminó el shim legado `scripts/detect_app_root.sh`, se limpiaron caches/artefactos obvios del repo y se borró `runs/` tras retirar sus últimas dependencias.

## Validación intentada
- `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_persistence_crud.py tests/test_api_articles.py` ✅
- `make check` ✅
- `make test` ✅
- El path de DB local con Docker Compose sigue siendo opcional y dependiente del host.

## Caveats
- Los nuevos tests de persistencia/API usan SQLite aislado para estabilidad local; no sustituyen una pasada de integración real contra Postgres.
- Los fixtures activos siguen usando el identificador histórico `20260314-1212-8ff9` para trazabilidad, pero ya viven bajo `tests/fixtures/evidence/...`.
- La validación Postgres local depende de que el host tenga Docker/Compose operativos.
