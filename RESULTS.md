# RESULTS.md — iter/021 three failing tests fixed

## Resumen breve

Iter/021 arregló exactamente los **tres tests rotos** que estaban tumbando `make test`, sin tocar lógica runtime fuera de contrato:
- contrato de métricas en `layered_discovery`
- aislamiento de entorno en el test de `LLMSettings`
- fixture manifest de traceability con el nombre/path viejo del repo

## Qué se hizo

- `tests/test_layered_discovery.py`
  - se actualizó `test_layered_discovery_tracks_rejected_noise_and_cap`
  - ahora espera el payload completo de métricas que `run_layered_discovery()` emite hoy:
    - `rejected_scope`
    - `rejected_stale`
    - `rejected_locality`
    - `rejected_article_type`
    - `same_local_day_candidates`
  - no se cambió la lógica de descubrimiento

- `tests/test_llm_client_usage.py`
  - se endureció `test_empty_generic_base_url_overrides_legacy_openrouter_base_url`
  - el test ahora limpia explícitamente vars ambiente que podían contaminar el caso:
    - `LLM_API_KEY`
    - `OPENAI_BASE_URL`
    - `OPENROUTER_API_KEY`
  - no se cambió la precedencia real de `LLMSettings.from_env()`; el fallo era del test, no del código

- `tests/fixtures/evidence/20260314-1212-8ff9/run_manifest.json`
  - se reemplazaron las rutas con repo viejo `scrape-spanish-news`
  - ahora apuntan al repo canónico actual `spain-news-bias-scraper`

## Verificación ejecutada

1. `uv run pytest -q tests/test_layered_discovery.py::test_layered_discovery_tracks_rejected_noise_and_cap tests/test_llm_client_usage.py::test_empty_generic_base_url_overrides_legacy_openrouter_base_url tests/test_run_traceability.py::RunTraceabilityTests::test_manifest_points_to_canonical_fixture_bundle`
2. `make test`

## Resultado de verificación

- los tres tests objetivo pasaron: **3 passed**
- `make test` pasó completo: **213 passed**

## Notas honestas

- el `.venv` del repo estaba enlazado a un intérprete inexistente (`/home/pi/...`) y era humo roto
- para la verificación se usó `uv run`, que recreó un entorno funcional y ejecutó pytest correctamente
- eso no cambió el alcance del fix; solo evitó pelearse con una venv hecha polvo

## Veredicto

Arreglo pequeño, limpio y sin teatro: tres fallos fuera, suite verde otra vez, y cero refactors disfrazados de virtud.
