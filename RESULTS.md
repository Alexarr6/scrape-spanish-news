# RESULTS.md — iter/009 implementer pass

## Resumen breve

Aterricé el slice aprobado: el guarded closure ahora puede **preservar raw components medium-only pequeños y coherentes** sin cambiar el método general ni abrir bridges blandos entre clusters ya formados.

## Qué cambié

### 1. Subfase nueva: `medium_component` preservation
En `src/analysis/pipeline.py` añadí una subfase entre el strong-core build y el singleton attach:

- inspecciona raw components usando sólo accepted edges no descartados
- considera únicamente componentes donde **todos los nodos siguen siendo singletons** tras el cierre por `strong`
- rescata sólo componentes de tamaño **2-3**
- exige coherencia mínima real:
  - score suficiente (`mean >= 0.72`, `best >= 0.74`)
  - ventana temporal corta (`days_delta <= 3`)
  - al menos una señal no trivial de tags/keyphrases
  - nada de secondary-form pairs
  - nada de `risky_bridge_pair`
  - nada de `entity_glue_penalty`, `late_story_drift_penalty` ni `secondary_form_penalty`

Traducción: rescata pares/cadenas medium que ya huelen bien, pero no convierte el cierre en una verbena de merges oportunistas.

### 2. Guardrail extra en `seed_pair`
Había una fuga fea: aunque la nueva preservación rechazase un medium pair sucio, el viejo `seed_pair` aún podía colarlo por el camino de singleton attach.

Lo cerré endureciendo `seed_pair` para que también rechace soporte con:
- `entity_glue_penalty`
- `late_story_drift_penalty`
- `secondary_form_penalty`
- `article_type_pair_class == secondary_form_pair`

Eso mantiene el comportamiento previo útil, pero ya no deja pasar basura por la puerta lateral.

## Tests añadidos/actualizados

En `tests/test_story_clustering.py` dejé cobertura dirigida para:

### Positivos
- medium-only pair limpio de tamaño 2 sobrevive como cluster final
- medium-only chain coherente de tamaño 3 sobrevive como cluster final

### Negativos
- medium-only pair con `entity_glue_penalty` no sobrevive
- medium-only pair de `secondary_form_pair` no sobrevive

También se mantuvieron verdes los tests previos de cierre/score/eval.

## Verificación ejecutada

```bash
/home/node/.local/bin/uv run pytest \
  tests/test_story_clustering.py \
  tests/test_story_pair_scoring.py \
  tests/test_story_matching_eval.py \
  tests/test_story_candidate_generation.py \
  tests/test_story_review.py
```

Resultado:
- `22 passed`

## Git / disciplina de alcance

- no mezclé `artifacts/` ni docs ajenos de explorer bias lens
- el cambio quedó acotado a pipeline + tests + docs de estado/log
- se creará commit atómico del slice implementado

## Lectura honesta

Este pase **no** abre puentes blandos generales entre non-singleton clusters. A propósito.

Lo que sí hace es dejar de matar algunos componentes raw medium-only que ya tenían pinta de mismo evento y que el cierre anterior tiraba por exceso de puritanismo. Es un primer rescate bounded, explicable y testeable.
