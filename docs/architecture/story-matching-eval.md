# Story matching evaluation scaffold

iter/009 Phase 0 deja una base mínima pero útil para medir el matching actual sin tocar todavía candidate generation v1, scorer v2 ni closure v2.

## Qué hay

- `src/analysis/story_eval.py`
  - construye artifacts de pares usando el scorer actual
  - evalúa labels de pares (`same_event` vs `different_event`)
  - evalúa clusters por pairwise cluster F1
  - exporta JSONL reproducible para auditoría
- `scripts/evaluate_story_matching.py`
  - ejecuta la baseline sobre un fixture gold set
  - genera `summary.json` y `pair-artifacts.jsonl`
- `scripts/bootstrap_story_gold_set.py`
  - genera un lote pequeño de pares candidatos para etiquetado manual
  - mezcla accepted high / borderline / rejected high para no sesgar la muestra
- `tests/fixtures/story_matching_eval_fixture.json`
  - fixture reproducible inicial
  - intentionally small: sirve para bloquear regresiones del baseline y demostrar el hueco de recall en follow-ups
- `tests/test_story_matching_eval.py`
  - test de baseline contractual

## Baseline reproducible actual

Con el fixture incluido y threshold `0.68`, el sistema actual deja este patrón:

- pair precision: `1.0`
- pair recall: `0.3333`
- pair F1: `0.5`
- cluster recall pairwise: `0.3333`
- predicted components: `[[1, 2], [3], [4], [5], [6]]`

Lectura directa: el pipeline actual acierta el core rewrite cercano (`1-2`), pero rompe el follow-up legítimo (`3`) aunque el gold lo considere mismo evento.

## Cómo correrlo

```bash
python3 scripts/evaluate_story_matching.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output-dir artifacts/story-matching-eval
```

```bash
python3 scripts/bootstrap_story_gold_set.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output artifacts/story-matching-eval/manual-gold-candidates.jsonl
```

## Formato esperado del gold manual

Cada fila del bootstrap deja:

- metadatos de ambos artículos
- score y razones del sistema actual
- huecos para `label` y `labeler_notes`

Labels recomendados por ahora:

- `same_event`
- `different_event`
- `uncertain`

## Limitaciones honestas

- Esta baseline es reproducible y útil, pero **no sustituye** un gold set real sobre artículos recientes de producción.
- El repo no deja hoy una ruta sencilla y estable a DB real en este entorno de subagente, así que el pase deja el andamiaje listo sin inventarse números “reales”.
- Aún no mide candidate recall porque el pipeline actual compara all-pairs dentro del slice cargado; esa métrica entra de verdad cuando exista candidate generation explícito.

## Siguiente paso sensato

Usar `bootstrap_story_gold_set.py` sobre una muestra más amplia/recent cuando el entorno tenga acceso operativo a DB o a un export de artículos enriquecidos. Con 50-150 pares manuales bien escogidos ya se puede distinguir si el agujero gordo está en:

1. follow-up misses
2. entity glue false merges
3. rewrites con titulares muy distintos
4. cierres de cluster demasiado conservadores
