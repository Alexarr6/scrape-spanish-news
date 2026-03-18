# STACK_CONTEXT.md — Data Pipeline

## Objetivo del pipeline

## Fuente(s) de datos
- Tipo (API/DB/CSV/stream):
- Frecuencia:
- Volumen estimado:

## Transformaciones
- Limpieza:
- Normalización:
- Enriquecimiento:

## Destino
- Sistema destino:
- Contrato de salida (schema):

## Calidad y observabilidad
- Validaciones de esquema:
- Reglas de calidad:
- Métricas/logs/alertas:

## Operación
- Scheduling:
- Retries/backoff:
- Gestión de fallos:

## Baseline Python (si aplica)
- Gestor de entorno/dependencias: `uv`
- Configuración canónica: `pyproject.toml`
- Lint/format: `ruff`
- Hooks de higiene: `pre-commit` con `ruff-check` y `ruff-format`
- Tests/linters/runs vía `uv run ...`
- Evitar dependencia de paquetes Python globales del host
