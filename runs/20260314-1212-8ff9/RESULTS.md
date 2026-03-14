# RESULTS.md

## Resumen
Implementación completada del PLAN con las decisiones humanas aprobadas:
1. ✅ `max-articles-to-extract` por defecto volvió a **120 global**.
2. ✅ Caídas >20% ya **no bloquean merge automáticamente**: se documentan como **WARNING** con diagnóstico y evidencia en este archivo.
3. ✅ Migración a `core/strategies` en este run: **solo EL PAÍS MVP** (reusable, mínima, reversible).

---

## Baseline canónico obligatorio (freeze)
Fecha fija: `2026-03-13`  
Caps fijos: `--max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180`

Comandos ejecutados:
```bash
python3 -m src.main --source elpais --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elpais_2026-03-13.json --metrics-out logs/canon_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elmundo_2026-03-13.json --metrics-out logs/canon_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_abc_2026-03-13.json --metrics-out logs/canon_abc_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_lavanguardia_2026-03-13.json --metrics-out logs/canon_lavanguardia_metrics.json
```

Snapshot canónico actual (after implementación):
- `elpais`: kept **27** (`discovered=164 processed=120 discarded_by_date=93 stop_reason=max_articles_to_extract`)
- `elmundo`: kept **25** (`discovered=72 processed=72 discarded_by_date=47 stop_reason=completed`)
- `abc`: kept **18** (`discovered=300 processed=120 discarded_by_date=102 stop_reason=max_articles_to_extract`)
- `lavanguardia`: kept **28** (`discovered=181 processed=120 discarded_by_date=92 stop_reason=max_articles_to_extract`)

Referencia canónica previa (PLAN): elpais 28, elmundo 25, abc 18, lavanguardia 27.

---

## Cambios implementados

### Fase 1 — Recovery mínima de cobertura EL PAÍS
- `src/main.py`
  - Default restaurado: `--max-articles-to-extract` de `100` ➜ `120`.

### Fase 2 — Arquitectura reusable `src/core/strategies` (EL PAÍS MVP)
Nuevos módulos:
- `src/core/strategies/base.py`
- `src/core/strategies/rss_discovery.py`
- `src/core/strategies/orchestrator.py`
- `src/core/strategies/__init__.py`

Migración EL PAÍS (solo MVP):
- `src/adapters/elpais.py`
  - Ahora usa `DiscoveryOrchestrator` + `RSSDiscoveryStrategy`.
  - Mantiene extracción/normalización existente (cambio mínimo y reversible).
  - Emite `strategy_metrics` en `logs/canon_elpais_metrics.json`.

Ejemplo `strategy_metrics` EL PAÍS:
```json
[
  {
    "strategy_name": "rss",
    "attempted": 164,
    "accepted": 164,
    "rejected_by_date": 0,
    "rejected_noise": 0,
    "errors": 0,
    "elapsed_ms": 885,
    "stop_reason": "completed"
  }
]
```

### Fase guardrails / no-regresión
- Tests ejecutados en verde:
  - `python3 -m src.main --help`
  - `python3 -m unittest discover -s tests -v` (9 tests OK)
- Nuevo test de strategies:
  - `tests/test_strategies.py` (deduplicación + cap candidates)

---

## Diagnóstico de no-regresión (con política de warning)
Comparativa against baseline canónico previo del PLAN:
- `elpais`: 28 ➜ 27 (**-3.6%**) ✅ dentro de tolerancia
- `elmundo`: 25 ➜ 25 (**0%**) ✅
- `abc`: 18 ➜ 18 (**0%**) ✅
- `lavanguardia`: 27 ➜ 28 (**+3.7%**) ✅

**No hubo caídas >20% en esta ejecución**, por lo que no se emite WARNING de regresión severa.

> Política aplicada: si en futuras corridas canónicas una fuente cae >20%, no se bloquea merge automáticamente; se debe añadir WARNING explícito con hipótesis y evidencia (métricas + comandos) en este `RESULTS.md`.

---

## Commits atómicos por fase
1. `2b1f40e` — `fix(cli): restore global default cap to 120 for canonical comparability`
2. `e5f85ba` — `refactor(core): add reusable discovery strategies MVP and migrate elpais`
3. `005b1a8` — `test(validation): add strategies test and refresh canonical evidence/results`

---

## Rollback
Rollback completo de esta entrega:
```bash
git revert --no-edit 005b1a8 e5f85ba 2b1f40e
```

Rollback por fases:
```bash
# deshacer validación/docs
git revert --no-edit 005b1a8
# deshacer migración strategies EL PAÍS MVP
git revert --no-edit e5f85ba
# deshacer cap global 120
git revert --no-edit 2b1f40e
```

Rollback rápido sin commits (working tree):
```bash
git restore src/main.py src/adapters/elpais.py src/core/strategies tests/test_strategies.py runs/20260314-0949-8e30/RESULTS.md
```
