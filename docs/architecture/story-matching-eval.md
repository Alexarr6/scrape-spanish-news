# Story matching evaluation + threshold review scaffold

iter/009 ya no deja sólo una baseline. Deja el circuito entero mínimo para iterar matching quality con humanos sin montar una UI pesada.

## Qué hay

### Base de evaluación
- `src/analysis/story_eval.py`
  - construye artifacts de pares usando el scorer actual
  - evalúa labels de pares (`same_event` vs `different_event`)
  - evalúa clusters por pairwise cluster F1
  - exporta JSONL reproducible para auditoría
- `scripts/evaluate_story_matching.py`
  - ejecuta la baseline sobre un fixture/export
  - genera `summary.json` y `pair-artifacts.jsonl`

### Threshold / calibration helpers
- `src/analysis/story_review.py`
  - sweep de thresholds
  - reporta métricas de pares y también métricas de cluster
  - selección de tandas revisables
  - render markdown para review humana
  - resumen de labels manuales
  - barrido de thresholds contra labels revisadas
- `scripts/compare_story_thresholds.py`
  - compara varios thresholds y deja salida JSON + Markdown
- `scripts/summarize_story_review_feedback.py`
  - resume feedback manual y prueba thresholds sobre esas revisiones

### Review batch humana
- `scripts/prepare_story_review_batch.py`
  - genera un batch pequeño de pares para revisar
  - deja `review-batch.jsonl` + `review-batch.md`
- `scripts/bootstrap_story_gold_set.py`
  - se puede seguir usando como scaffold crudo si hace falta

### Tests / fixture
- `tests/fixtures/story_matching_eval_fixture.json`
  - fixture reproducible inicial
  - intentionally small: sirve para bloquear regresiones y demostrar el hueco de recall en follow-ups
- `tests/test_story_matching_eval.py`
- `tests/test_story_review.py`

## Baseline reproducible actual

Con el fixture incluido y threshold `0.68`, el sistema deja este patrón:

- pair precision: `1.0`
- pair recall: `0.3333`
- pair F1: `0.5`
- cluster recall pairwise: `0.3333`
- predicted components: `[[1, 2], [3], [4], [5], [6]]`

Lectura directa: el pipeline acierta el rewrite cercano (`1-2`), pero rompe el follow-up legítimo (`3`) aunque el gold lo considere mismo evento.

## Cómo usar el workflow práctico

### 1) Medir baseline / artifact dump

```bash
python3 scripts/evaluate_story_matching.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output-dir artifacts/story-matching-eval
```

### 2) Comparar thresholds

```bash
python3 scripts/compare_story_thresholds.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --thresholds 0.45,0.55,0.60,0.68,0.72,0.78 \
  --output-dir artifacts/story-threshold-compare
```

Salida útil:
- `summary.json`
- `summary.md`

Ambos incluyen ya:
- métricas de pares
- métricas de cluster

### 3) Preparar tanda humana de 5-10 pares

```bash
python3 scripts/prepare_story_review_batch.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output-dir artifacts/story-review-batch \
  --batch-size 8
```

Salida útil:
- `review-batch.jsonl`
- `review-batch.md`
- `manifest.json`

La selección mezcla:
- `accepted_high`
- `borderline`
- `rejected_high`

Eso permite revisar justo la zona donde el threshold importa de verdad.

### 4) Etiquetar manualmente

Editar `review-batch.jsonl` y rellenar:
- `label`: `same_event` / `different_event` / `uncertain`
- `labeler_notes`: libre

### 5) Resumir feedback y probar thresholds sobre esas labels

```bash
python3 scripts/summarize_story_review_feedback.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --review-jsonl artifacts/story-review-batch/review-batch.jsonl \
  --thresholds 0.45,0.55,0.60,0.68,0.72,0.78 \
  --output-dir artifacts/story-review-feedback
```

## Formato de revisión manual

Cada fila de `review-batch.jsonl` deja:

- bucket de muestreo
- ids del par
- predicción actual
- score
- `candidate_rank`
- `candidate_origins`
- `reason` completo del scorer
- title + summary de ambos artículos
- huecos para `label` y `labeler_notes`

Y `review-batch.md` lo renderiza de forma cómoda para revisar por chat en tandas pequeñas.

## Limitaciones honestas

- Este workflow ya es útil, pero **no sustituye** un gold set real sobre artículos recientes de producción.
- El fixture sirve para bloqueo de regresiones y para probar la operativa, no para sacar conclusiones globales.
- Si no hay export reciente o acceso a DB/enriched sample, la calibración sigue siendo parcial.

## Siguiente paso sensato

Usar este flujo sobre un export reciente de artículos enriquecidos y etiquetar 50-150 pares en tandas pequeñas. Con eso ya se podrá separar con bastante menos humo:

1. follow-up misses
2. entity glue false merges
3. rewrites con titulares muy distintos
4. opinion bleed
5. thresholds demasiado conservadores o demasiado blandos
