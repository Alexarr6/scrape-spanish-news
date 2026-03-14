# RESULTS.md

## Resumen
Integración de **20minutos** completada respetando arquitectura **core + adapters**, baseline canónico, guardrails y commits atómicos.

Fecha canónica usada: **2026-03-13**.

---

## 0) Preflight + baseline canónico
Comandos:
```bash
python3 -V
python3 -m src.main --help
python3 -m unittest discover -s tests -v
```

Resultado preflight:
- Python `3.11.2`
- Help OK con `--source {20minutos,abc,elmundo,elpais,lavanguardia}`
- Tests: `10 passed`

Baseline canónico (fuentes previas):
```bash
python3 -m src.main --source elpais --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elpais_2026-03-13.json --metrics-out logs/canon_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elmundo_2026-03-13.json --metrics-out logs/canon_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_abc_2026-03-13.json --metrics-out logs/canon_abc_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_lavanguardia_2026-03-13.json --metrics-out logs/canon_lavanguardia_metrics.json
```

Conteos baseline:
- `elpais`: **26**
- `elmundo`: **25**
- `abc`: **15**
- `lavanguardia`: **27**

---

## 1) Discovery 20minutos (RSS -> sitemap -> HTML fallback)
Documento: `docs/DISCOVERY_20MINUTOS.md`

Estrategia implementada:
1. RSS primario (`/rss/`, `/rss/nacional/`, `/rss/actualidad/`)
2. Sitemap fallback (`sitemap-noticias`, `sitemap-news`, `sitemap.xml`)
3. HTML fallback (`/nacional/`, `minuteca/politica`, `minuteca/espana`)

Scope inicial aplicado: España/política/nacional relacionadas.

Guardrails activos:
- timeout HTTP con retries/backoff (core `HttpClient`)
- límites de runtime/discovery/extracción por `RunConfig`
- dedupe por URL
- filtrado temático por whitelist

---

## 2) Adapter + CLI + contrato de salida
Cambios relevantes:
- `src/adapters/minutos20.py` (nuevo adapter)
- `src/adapters/registry.py` (alta de `20minutos`)
- `src/main.py` (CLI expone fuente nueva)
- `tests/test_20minutos_adapter.py` (discovery por capas)

CSV opcional con inferencia por extensión validado:
```bash
python3 -m src.main --source 20minutos --date 2026-03-13 --out data/news_20minutos_2026-03-13.csv --metrics-out logs/news_20minutos_metrics_csv.json
```

---

## 3) Validación comparativa final
Runs finales ejecutados:
```bash
python3 -m src.main --source elpais --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elpais_2026-03-13.json --metrics-out logs/canon_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_elmundo_2026-03-13.json --metrics-out logs/canon_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_abc_2026-03-13.json --metrics-out logs/canon_abc_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/canon_lavanguardia_2026-03-13.json --metrics-out logs/canon_lavanguardia_metrics.json
python3 -m src.main --source 20minutos --date 2026-03-13 --max-discovery-urls 300 --max-articles-to-extract 120 --max-runtime-seconds 180 --out data/news_20minutos_2026-03-13.json --metrics-out logs/news_20minutos_metrics.json
```

Comparativa baseline vs final (fuentes previas):
- `elpais`: 26 -> **25** (-3.8%)
- `elmundo`: 25 -> **25** (0.0%)
- `abc`: 15 -> **14** (-6.7%)
- `lavanguardia`: 27 -> **27** (0.0%)

Política no-regresión aplicada:
- No hay caída >20% -> **sin warning bloqueante**.
- Diferencias menores documentadas arriba con diagnóstico por métricas.

Métricas finales por fuente:
- `elpais`: discovered=164, processed=120, kept=25, discarded_by_date=95, stop_reason=`max_articles_to_extract`
- `elmundo`: discovered=73, processed=73, kept=25, discarded_by_date=48, stop_reason=`completed`
- `abc`: discovered=300, processed=120, kept=14, discarded_by_date=106, stop_reason=`max_articles_to_extract`
- `lavanguardia`: discovered=182, processed=120, kept=27, discarded_by_date=93, stop_reason=`max_articles_to_extract`
- `20minutos`: discovered=34, processed=34, kept=20, discarded_by_date=14, stop_reason=`completed`

Muestra de titulares (top-3 por fuente):
- `elpais`
  1. ‘Torrente presidente’: soez, excesiva y por momentos muy divertida
  2. La justicia venezolana niega el derecho a la amnistía a Perkins Rocha, el abogado de María Corina Machado
  3. La exconsejera de Mazón investigada en la dana se muestra “convencida” de que no irá a prisión
- `elmundo`
  1. El Gobierno recoloca en secreto en Adif al mismo cargo al que cesó por la crisis de Rodalies
  2. El 'cambio de cara' de Vox: una pasarela de aliados de Abascal para blindarse el 15-M
  3. El instituto con dificultades que ahora es el más demandado con un dictado y una hora de lectura en clase cada día
- `abc`
  1. Votar es defender la democracia
  2. Desde Bolivia para el mundo: Felipe VI debuta en TikTok con un viejo amigo de juventud
  3. Bolaños amplía el plazo de candidaturas a juez del TEDH... un día
- `lavanguardia`
  1. ¿Sánchez está “jodío”?, por Isabel Garcia Pagan
  2. Fernández Díaz y Ábalos, en el banquillo: una singular coincidencia
  3. Sánchez agita el no a la guerra: “Hoy España reivindica la paz y la derecha reivindica a Aznar”
- `20minutos`
  1. EEUU pide a sus ciudadanos que estén alerta ante "amenazas" en las manifestaciones en España por la guerra de este sábado
  2. El Gobierno contempla bajar el IVA de la luz para contener los precios ante la crisis por la guerra de Irán
  3. Un fallo de Hacienda deja sin combustible al cuarto mayor distribuidor de España y afecta a 570 gasolineras

---

## 4) Commits atómicos (entrega 20minutos)
1. `c0dd9e8` — `chore(baseline): freeze canonical regression baseline for existing sources`
2. `d90ac17` — `docs(discovery): define 20minutos ingestion strategy and guardrails`
3. `ad60dc2` — `feat(adapter): add 20minutos adapter with utc date filter and guardrails`
4. `c482178` — `feat(cli): wire 20minutos source into multi-source command routing`
5. `5e84f7e` — `test(validation): add comparative regression evidence for existing sources + 20minutos`

---

## 5) Rollback
Rollback total:
```bash
git revert --no-edit 5e84f7e c482178 ad60dc2 d90ac17 c0dd9e8
```

Rollback por fase:
```bash
git revert --no-edit 5e84f7e   # validación comparativa
git revert --no-edit c482178   # wiring CLI
git revert --no-edit ad60dc2   # adapter 20minutos
git revert --no-edit d90ac17   # docs discovery
git revert --no-edit c0dd9e8   # baseline
```

---

## 6) Phase-1 baseline (quick wins preflight)
Comandos ejecutados desde `runs/20260314-1212-8ff9`:
```bash
pwd
git rev-parse --show-toplevel
git rev-parse --short HEAD
git status --short
python3 -m src.main --help
python3 -m unittest discover -s tests -v
```

Resultado baseline:
- evidencia completa guardada en `logs/phase1_baseline.txt`
- `pwd`: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper/runs/20260314-1212-8ff9`
- `git rev-parse --show-toplevel`: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- `git rev-parse --short HEAD`: `2ccf3a9`
- CLI help: OK (`--source` incluye `{20minutos,abc,eldiario,elmundo,elpais,lavanguardia}`)
- Suite tests baseline: OK (`11 passed` antes de añadir contratos)

## 7) Phase-1 quick wins implemented

### 7.1 Traceability mismatch fix (safe)
**Before:** ambigüedad entre run implementador (`1212-8ff9`) y run de review (`1250-edr1`) sin puntero machine-readable.

**After:**
- `RUN_MANIFEST.md` define root canónico, companion run y comandos reproducibles.
- `run_manifest.json` añade puntero machine-readable con `canonical_run_id`, rutas y `verify_commands`.
- `tests/test_run_traceability.py` falla si se rompe/ausenta la trazabilidad.

### 7.2 `comparison_summary` schema standardized
**Before:** `logs/comparison_summary.json` tenía drift (`regression[]` + `source_20minutos` fuera de colección homogénea).

**After:**
- Contrato v1 documentado: `docs/contracts/comparison_summary.schema.json`.
- Builder estable: `src/core/comparison_summary.py`.
- Generador reproducible: `scripts/generate_comparison_summary.py`.
- Salida normalizada: `logs/comparison_summary.json` con contrato único:
  - metadatos globales (`generated_at`, `date`, `baseline_ref`, `current_ref`)
  - estado/warnings globales
  - `sources[]` homogéneo por fuente
  - métricas mínimas estables (`discovered`, `processed`, `kept`, `discarded_by_date`, `stop_reason`)

### 7.3 Integration/contract tests for schema stability
Nuevos tests:
- `tests/test_comparison_summary_contract.py`
- `tests/test_cross_source_output_metrics_contract.py`
- `tests/test_run_traceability.py`

Validación final:
```bash
python3 scripts/generate_comparison_summary.py --date 2026-03-13 --out logs/comparison_summary.json
python3 -m unittest discover -s tests -v
```
- Generación summary: OK (`6 source rows`)
- Suite total: OK (`15 passed`)

## 8) Rollback hints (Phase-1 quick wins)
Rollback completo de quick wins (después de crear commits faseados):
```bash
# usar hashes de los commits de quick wins (ver git log --oneline)
git revert --no-edit <phase1-docs-traceability> <phase1-schema-normalization> <phase1-contract-tests> <phase1-results>
```

Rollback por bloque:
```bash
git revert --no-edit <phase1-docs-traceability>
git revert --no-edit <phase1-schema-normalization>
git revert --no-edit <phase1-contract-tests>
git revert --no-edit <phase1-results>
```

---


## 9) Hardening wave (A/B/C) — 2026-03-14

### Phase A — Core contracts
Implemented core contract models in `src/core/contracts.py` and wired validation bridges at boundaries:
- `src/core/adapter.py` now validates `metrics` via `validate_metrics_payload`.
- `src/core/export.py` validates article payloads before JSON/CSV write.
- `src/core/comparison_summary.py` validates final summary payload before return.

Compatibility note:
- Legacy `strategy_metrics` list payloads are still accepted and normalized to envelope form for backward compatibility.

Commit:
- `e74ebcd` — `feat(core): add pydantic-style contract models for news and metrics payloads`

### Phase B — Stronger contract tests + fixtures
Added deterministic contract fixtures and negative tests:
- `tests/test_contract_models.py`
- `tests/fixtures/comparison_summary_valid.json`
- Strengthened:
  - `tests/test_comparison_summary_contract.py`
  - `tests/test_cross_source_output_metrics_contract.py`

Includes:
- Required/missing field failures
- Type mismatch failures
- Comparison summary schema assertions (`model_json_schema` shape)

Commit:
- `d4780e4` — `test(contract): enforce schema validation for news, metrics, and comparison summary`

### Phase C — One low-risk standardization beyond ElPais
Standardized ElDiario discovery instrumentation to strategy-envelope shape without changing discovery order (RSS -> sitemap(+robots) -> HTML fallback):
- `src/core/strategies/metrics.py` (shared envelope helper)
- `src/adapters/eldiario.py` emits `strategy_metrics` envelope
- `src/adapters/elpais.py` aligned to same envelope helper
- `tests/test_eldiario_adapter.py` extended with envelope assertion

Commit:
- `f038c11` — `refactor(discovery): standardize eldiario discovery metrics envelope`

### Verification evidence
Commands executed (from canonical root `runs/20260314-1212-8ff9`):
```bash
python3 -m unittest discover -s tests -v
python3 -m src.main --help
python3 -m src.main --source eldiario --date 2026-03-13 --out data/standardized_eldiario.json --metrics-out logs/standardized_eldiario_metrics.json --max-runtime-seconds 20
python3 - <<'PY'
import json
m=json.load(open('logs/standardized_eldiario_metrics.json'))
print(sorted(m.keys()))
print(m.get('strategy_metrics',{}).get('schema_version'))
print(len(m.get('strategy_metrics',{}).get('strategies',[])))
PY
```

Observed:
- Test suite: **21 passed**
- CLI help: OK
- ElDiario smoke: `kept=20`, `stop_reason=max_runtime_seconds`
- `strategy_metrics.schema_version`: `discovery_strategy_metrics.v1`
- `strategy_metrics.strategies` length: `3`

### Rollback hints (hardening wave)
```bash
# Revert docs/evidence commit (this section)
git revert --no-edit <docs-results-commit>

# Revert phase C only
git revert --no-edit f038c11

# Revert phase B only
git revert --no-edit d4780e4

# Revert phase A only
git revert --no-edit e74ebcd
```

## 10) Persistence + API v1 (Postgres-only, opt-in) — 2026-03-14

Confirmed decisions implemented:
1. Postgres-only target (no SQLite path)
2. Idempotency key v1 = `(source, url)`
3. Persistence opt-in via `--persist` / `--db-url`
4. API v1 minimal endpoints

### Structure delivered (separated modules)
- **Core contracts** (existing scraper contracts + article_text):
  - `src/core/models.py`
  - `src/core/contracts.py`
- **ORM models**:
  - `src/persistence/orm_models.py`
- **CRUD access layer**:
  - `src/persistence/crud.py`
- **Pydantic operation-oriented schemas**:
  - `src/persistence/contracts.py` (`ArticleCreate`, `ArticleRead`, `ArticleUpdate`, `ArticleDelete`, `IngestResult`)
- **DB/session wiring**:
  - `src/persistence/db.py`
- **FastAPI v1 minimal surface**:
  - `src/api/v1/articles.py`
  - `src/api/app.py` (factory mode)

### End-to-end `article_text`
`article_text` now flows through:
- core article dataclass (`src/core/models.py`)
- validation contract (`src/core/contracts.py`)
- exports JSON/CSV (`src/core/export.py`)
- persistence schemas + ORM + upsert (`src/persistence/*`)
- API payload models and endpoints (`src/api/v1/articles.py`)

### CLI compatibility + opt-in persistence
- `src/main.py` keeps previous behavior by default.
- New flags:
  - `--persist` (disabled by default)
  - `--db-url` (used only if `--persist` enabled)
- If not using `--persist`, no DB path is invoked (existing output flow intact).

### Verification evidence (executed)
Commands run:
```bash
PYTHONPATH=runs/20260314-1212-8ff9 python3 -m src.main --help | head -80
PYTHONPATH=runs/20260314-1212-8ff9 python3 -m unittest \
  runs/20260314-1212-8ff9/tests/test_models.py \
  runs/20260314-1212-8ff9/tests/test_contract_models.py \
  runs/20260314-1212-8ff9/tests/test_export_article_text.py
```
Observed output:
- CLI help includes new flags: `--persist`, `--db-url`
- Unit tests: `Ran 6 tests ... OK`

### Rollback hints (this increment)
Targeted rollback commands (when commit hashes are available):
```bash
# 1) API layer
git revert --no-edit <feat-api-v1-minimal>

# 2) Persistence contracts/ORM/CRUD
git revert --no-edit <feat-persistence-postgres-idempotent>

# 3) CLI opt-in persistence + article_text export path
git revert --no-edit <feat-cli-persist-optin-article-text>

# 4) Verification docs section
git revert --no-edit <docs-results-persistence-section>
```
