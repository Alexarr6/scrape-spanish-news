# RESULTS.md — iter/022 ambiguous legacy/manual surface classification

## Resumen breve

Iter/022 cerró la ambigüedad de tres superficies que seguían oliendo a deuda pero no tenían prueba de borrado seguro:

- `src/core/strategies/rss_discovery.py` + `src/core/strategies/__init__.py` → **`safe remove later`**
- scripts de story-matching / review en `scripts/` → **`manual-but-supported`**
- `scripts/run_scheduled.sh` → **`legacy-but-retained`**
- ayuda/prominencia Makefile del scheduler legacy → **`safe demote`**

Además se hizo un cambio mínimo y honesto: `make help` ahora pone primero la superficie canónica de refresh y baja los helpers legacy a una sección explícitamente no canónica.

## Clasificación detallada con evidencia

### 1) `src/core/strategies/rss_discovery.py` y `src/core/strategies/__init__.py`

**Clasificación:** `safe remove later`

**Evidencia:**
- `RSSDiscoveryStrategy` sólo aparece en:
  - `src/core/strategies/rss_discovery.py`
  - `src/core/strategies/__init__.py`
- no hay importadores en `src/`, `scripts/`, `tests/`, `docs/`, `README.md` o `Makefile` que consuman `RSSDiscoveryStrategy`
- las referencias activas a `rss_discovery` son etiquetas de métricas/nombre de estrategia en el flujo vivo de `src/adapters/profiled_adapter.py` y tests (`strategy_name="rss_discovery"`), no wiring al módulo ni a la clase
- `tests/test_strategies.py` importa `DiscoveryOrchestrator` directamente desde `src.core.strategies.orchestrator`, no desde el barrel `src.core.strategies`
- la única acoplación in-tree restante es la re-export en `src/core/strategies/__init__.py`

**Por qué no quedó en `keep`:**
- no hay wiring runtime vivo hacia `RSSDiscoveryStrategy`
- el barrel export no basta para llamarlo superficie soportada real; eso es residuo de compatibilidad hasta que alguien pruebe lo contrario

**Por qué no se borró ahora:**
- el único residuo real es precisamente un export de compatibilidad
- sin prueba sobre imports externos/fuera del repo, borrarlo en esta iteración habría sido adivinar con confianza, que es una forma elegante de hacer el idiota

### 2) Story-matching / review helper scripts en `scripts/`

**Clasificación:** `manual-but-supported`

**Superficie incluida:**
- `scripts/bootstrap_story_gold_set.py`
- `scripts/compare_story_thresholds.py`
- `scripts/evaluate_story_matching.py`
- `scripts/prepare_story_review_batch.py`
- `scripts/summarize_story_review_feedback.py`

**Evidencia:**
- los cinco scripts tienen CLI real con `argparse` y guard `if __name__ == "__main__"`
- todos cargan dataset/fixture real y se apoyan en código vivo de librería:
  - `src.analysis.story_eval`
  - `src.analysis.story_review`
  - `src.analysis.pipeline.ClusterPipeline`
- `docs/architecture/story-matching-eval.md` documenta el flujo completo con comandos reproducibles y rutas de salida actuales:
  - baseline: `scripts/evaluate_story_matching.py` → `artifacts/story-matching-eval`
  - threshold sweep: `scripts/compare_story_thresholds.py` → `artifacts/story-threshold-compare`
  - review batch: `scripts/prepare_story_review_batch.py` → `artifacts/story-review-batch`
  - feedback summary: `scripts/summarize_story_review_feedback.py` → `artifacts/story-review-feedback`
  - bootstrap helper: `scripts/bootstrap_story_gold_set.py`
- la documentación describe una secuencia manual coherente: medir baseline → comparar thresholds → preparar batch humano → etiquetar → resumir feedback
- `tests/test_story_matching_eval.py` y `tests/test_story_review.py` cubren los módulos de soporte vivos aunque no invoquen los wrappers CLI directamente

**Matiz importante:**
- `bootstrap_story_gold_set.py` es el más scaffold de la familia y el propio doc ya lo llama `scaffold crudo si hace falta`
- aun así, sigue encajando en el mismo workflow manual y no merece una sentencia fake de “dead code”

**Por qué no quedó en `keep`:**
- no forma parte del happy path operador principal
- no está expuesto vía Makefile/README como flujo producto
- su naturaleza es manual/calibración, no runtime canónico

### 3) `scripts/run_scheduled.sh` + superficie legacy relacionada

#### `scripts/run_scheduled.sh`
**Clasificación:** `legacy-but-retained`

**Evidencia:**
- el script es plenamente runnable hoy: hace preflight, `run-all-persist`, `verify-output`, `verify-db`, locking, retry, logging y state files bajo `var/`
- emite un warning explícito de legado:
  - `LEGACY scrape-only wrapper: this script does not run enrich-articles or build-story-clusters...`
- README y docs lo describen como wrapper legacy/deprecated, mientras presentan como superficie canónica:
  - `scripts/run_stories_refresh.sh`
  - `scripts/run_explorer_refresh.sh`
  - `make full-refresh-once`
- `docs/operator-guide/workflows.md` y `docs/operator-guide/scheduler.md` ya separan el camino activo del camino legacy

**Por qué no quedó en `safe remove later`:**
- no es residuo inerte; todavía ejecuta lógica útil y mantiene continuidad operativa para scrape + verify
- no tenemos prueba de ausencia total de dependencia externa/operator

#### Makefile legacy scheduler help surface (`scheduler-dry-run`, `scheduler-once`, `status`, `tail-log`)
**Clasificación:** `safe demote`

**Evidencia:**
- los targets son wrappers finos alrededor del script/state/log legacy, así que siguen siendo reales
- pero `make help` todavía les daba demasiado protagonismo en la misma cabecera que la superficie canónica de refresh
- eso mantenía una UX medio mentirosa: el repo ya tiene wrappers mejores, pero la ayuda seguía enseñando antes el martillo viejo

**Cambio mínimo aplicado:**
- `make help` ahora muestra primero `stories-refresh-once`, `explorer-refresh-once`, `full-refresh-once`, `verify-output`, `verify-db`
- los comandos legacy bajan a una sección separada:
  - `Legacy scheduler helpers (retained, not canonical)`

**Por qué este cambio sí estaba justificado:**
- no cambia comportamiento
- sólo alinea la superficie visible con la verdad operativa ya documentada en README/docs/script warning

## Verificación ejecutada

1. búsqueda repo-wide de referencias a `RSSDiscoveryStrategy` / `rss_discovery`
2. inspección directa de:
   - `src/core/strategies/rss_discovery.py`
   - `src/core/strategies/__init__.py`
   - story-review scripts bajo `scripts/`
   - `scripts/run_scheduled.sh`
   - `Makefile`
   - `docs/architecture/story-matching-eval.md`
   - `docs/operator-guide/scheduler.md`
   - `docs/operator-guide/workflows.md`
3. `make help`

## Resultado de verificación

- `make help` pasó y refleja correctamente la democión de la superficie legacy
- la clasificación queda cerrada sin borrado especulativo

## Veredicto

La deuda que quedaba aquí no era “basura obvia”. Era mezcla de compatibilidad residual, tooling manual útil y una superficie legacy demasiado visible. Ya está clasificada sin teatro, que era justo el puto trabajo.