# RESULTS.md

## Resumen de entrega

Se promovió la app canónica desde `runs/20260314-1212-8ff9/` a la raíz del repo. La raíz ya contiene `src/`, `tests/` y los assets mínimos necesarios para operar y testear. `runs/` queda como archivo/evidencia, no como dependencia de runtime.

## Cambios realizados
- `src/` promovido a raíz como código canónico.
- `tests/` promovido a raíz como suite canónica.
- `docs/contracts/comparison_summary.schema.json` promovido a raíz.
- `scripts/generate_comparison_summary.py` promovido a `scripts/`.
- `pyproject.toml` actualizado para describir la app real y añadir `psycopg[binary]`.
- `src/persistence/db.py` actualizado para normalizar URLs PostgreSQL hacia `postgresql+psycopg://`.
- `Makefile`, `scripts/detect_app_root.sh` y `scripts/run_scheduled.sh` simplificados para usar la raíz como único app root.
- `README.md`, `.gitignore` y `STATUS.md` actualizados al flujo root-first real.
- tests de evidencia adaptados para leer fixtures archivados desde `runs/20260314-1212-8ff9/` sin reintroducir dependencia de runtime.

## Validación intentada
- Pendiente ejecutar la batería completa en este host tras regenerar `uv.lock` con `uv sync`.
- El path de DB local sigue dependiendo de Docker Compose disponible en host.

## Caveats
- Los tests de contratos/evidencia siguen leyendo artefactos archivados de `runs/20260314-1212-8ff9/`; eso es intencional y ya no afecta al runtime.
- No se borró ni reescribió historia bajo `runs/`.
