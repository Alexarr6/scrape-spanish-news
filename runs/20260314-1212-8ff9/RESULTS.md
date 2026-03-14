# RESULTS.md

## Resumen
Implementación de `20minutos` completada en run `20260314-1212-8ff9` respetando core+adapters, baseline canónico, guardrails y validación de no-regresión.

Fecha canónica usada en todo el run: **2026-03-13**.

---

## Fase 0 — Baseline canónico (antes de cambios)
Preflight ejecutado:
```bash
python3 -V
python3 -m src.main --help
python3 -m unittest discover -s tests -v
```

Baseline congelado:
```bash
python3 -m src.main --source elpais --date 2026-03-13 --out data/canon_elpais_2026-03-13.json --metrics-out logs/canon_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --out data/canon_elmundo_2026-03-13.json --metrics-out logs/canon_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --out data/canon_abc_2026-03-13.json --metrics-out logs/canon_abc_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --out data/canon_lavanguardia_2026-03-13.json --metrics-out logs/canon_lavanguardia_metrics.json
```

Conteos baseline:
- `elpais`: 26
- `elmundo`: 25
- `abc`: 15
- `lavanguardia`: 27

---

## Fase 1 — Discovery 20minutos
Documento: `docs/DISCOVERY_20MINUTOS.md`

Estrategia final:
1. **RSS primario** (`/rss/`, `/rss/nacional/`, `/rss/actualidad/`)
2. **Sitemap fallback** (candidatos mantenidos, no bloqueantes)
3. **HTML fallback** (`/nacional/`, `minuteca/politica`, `minuteca/espana`)

Whitelist temática inicial: España / política / nacional.

---

## Fase 2-3 — Adapter + CLI
Cambios principales:
- nuevo adapter: `src/adapters/minutos20.py`
- registro CLI: `src/adapters/registry.py` añade `20minutos`
- test adapter: `tests/test_20minutos_adapter.py`
- test registry actualizado para incluir `20minutos`

Verificación:
```bash
python3 -m src.main --help
python3 -m unittest discover -s tests -v
python3 -m src.main --source 20minutos --date 2026-03-13 --out data/news_20minutos_2026-03-13.json --metrics-out logs/news_20minutos_metrics.json
```

Resultado `20minutos`:
- kept: **20**
- stop_reason: `completed`

Muestra de titulares (20minutos):
- "Huelga de basuras de Madrid, en directo: el Ayuntamiento espera que hoy se alcance un acuerdo para desconvocar el paro"
- "Feijóo no quiere amnistía, pero sí para su hermano"
- "Puigdemont reclama al PSOE "cumplir íntegramente" los pactos y no "rebajar" la ley de amnistía"

---

## Fase 4 — No-regresión final
Regeneración final fuentes previas:
```bash
python3 -m src.main --source elpais --date 2026-03-13 --out data/reg_elpais_2026-03-13.json --metrics-out logs/reg_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --out data/reg_elmundo_2026-03-13.json --metrics-out logs/reg_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --out data/reg_abc_2026-03-13.json --metrics-out logs/reg_abc_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --out data/reg_lavanguardia_2026-03-13.json --metrics-out logs/reg_lavanguardia_metrics.json
```

Comparativa baseline vs final:
- `elpais`: 26 → 26 (0.0%)
- `elmundo`: 25 → 25 (0.0%)
- `abc`: 15 → 15 (0.0%)
- `lavanguardia`: 27 → 27 (0.0%)

No hay caída relevante; no aplica warning de regresión.

Resumen estructurado adicional: `logs/comparison_summary.json`.

---

## Commits atómicos + rollback
1. `chore(baseline): freeze canonical regression baseline for existing sources`
2. `docs(discovery): define 20minutos ingestion strategy and guardrails`
3. `feat(adapter): add 20minutos adapter with utc date filter and guardrails`
4. `feat(cli): wire 20minutos source into multi-source command routing`
5. `test(validation): add comparative regression evidence for existing sources + 20minutos`

Rollback total de esta entrega:
```bash
git revert --no-edit <validation_commit> c482178 ad60dc2 d90ac17 c0dd9e8
```

Rollback por fase:
```bash
git revert --no-edit <validation_commit>   # validación + evidencia final
git revert --no-edit c482178   # wiring CLI
git revert --no-edit ad60dc2   # adapter 20minutos
git revert --no-edit d90ac17   # docs discovery
git revert --no-edit c0dd9e8   # baseline canónico
```
