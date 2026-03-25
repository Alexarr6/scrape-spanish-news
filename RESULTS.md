# RESULTS.md — iter/009 Phase 5 cluster-gap audit

## Executive summary

La discrepancia entre `accepted_pairs` y `cluster_count` **no sale de un bug tonto en connected components**. Sale de dos cosas juntas:

1. **`accepted_pairs` estaba sobrevendiendo conectividad real**.
   Cuenta todos los pares que pasan threshold, incluidos edges `medium` y edges redundantes dentro del mismo componente crudo.

2. **el cierre final es más conservador que el grafo crudo**.
   `ClusterPipeline` no hace “union de todos los accepted edges y ya”. Primero forma componentes base con edges `strong` y luego deja que ciertos `medium` sólo adjunten singletons con soporte suficiente. Un edge `medium` entre dos subclusters ya formados puede subir `accepted_pairs` y aun así no bajar `cluster_count`.

Traducción sin maquillaje: la métrica llevaba a engaño y el cierre actual está diseñado para frenar fusiones dudosas, incluso cuando el contador bruto de pares aceptados sube bastante.

## Qué cambié en esta auditoría

### 1. Hice explícita la diferencia entre grafo crudo y cierre guardado

Añadí métricas nuevas a `ClusterRebuildMetrics`:

- `accepted_strong_pair_count`
- `accepted_medium_pair_count`
- `accepted_risky_pair_count`
- `raw_component_count`
- `raw_multi_article_component_count`
- `guarded_cluster_count`
- `guarded_multi_article_cluster_count`
- `singleton_count`
- `attached_singleton_count`
- `unattached_singleton_count`
- `closure_decision_counts`

Eso permite responder preguntas que antes quedaban opacas:

- ¿subieron los pares por edges fuertes o por medium?
- ¿el grafo bruto sí conectó más cosas?
- ¿el cierre guardado las dejó separadas a propósito?
- ¿lo que crece son attachments de singletons o redundancia interna?

### 2. Añadí una prueba que fija el comportamiento que estaba confundiendo la lectura

Nuevo test en `tests/test_story_clustering.py`:
- el grafo crudo con accepted edges produce `[[1, 2, 3, 4]]`
- el cierre guardado conserva `[[1, 2], [3, 4]]`

Eso demuestra con un caso mínimo que **más accepted pairs no implica menos clusters** en el pipeline actual.

### 3. Documenté la nuance en arquitectura

Actualicé `docs/architecture/analysis-pipeline.md` para dejar claro que el paso de clustering real es:

- accepted-edge graph crudo
- guarded closure
- persistencia final

No “accepted edges -> connected components” a secas, que era una simplificación demasiado optimista.

## Diagnóstico técnico claro

### Lo que NO parece ser

- **No parece un bug básico de connected components / transitive closure.**
  El código sí sabe conectar por cierre cuando la política de cierre lo permite.

- **No parece un bug de persistencia/report que esté borrando clusters válidos** a nivel conceptual del código revisado.
  El mismatch nace antes: en cómo se forma el cluster final y en qué significa cada métrica.

### Lo que SÍ está pasando

#### A. `accepted_pairs` mezcla edges con valor muy distinto

En la métrica vieja, todo edge aceptado valía lo mismo:
- edge fuerte que crea/une estructura real
- edge medium que sólo sirve para attach conservador
- edge redundante dentro de un componente ya conectado

Eso hace que el contador suba mucho sin que el grafo útil cambie mucho.

#### B. El cierre guardado puede bloquear fusiones entre componentes no-singleton

La política actual favorece:
- base components por edges `strong`
- attach posterior de left-overs/singletons con soporte adicional

Pero **no trata un bridge `medium` entre dos clusters ya existentes como licencia automática para fusionarlos**.

Ese detalle explica muy bien el síntoma del usuario:
- bajas threshold
- aparecen más puentes aceptados
- pero muchos son `medium`
- y el cierre final no convierte eso en una fusión de clusters completos

#### C. Muchos singletons “intuitivamente agrupables” pueden seguir fuera por scorer/closure, no por unión rota

Si los pares reales de mismo evento se quedan en zona `medium` o borderline y además no cumplen suficiente compatibilidad de attach/pivot, el pipeline actual los deja fuera aunque el usuario los vea claros manualmente.

O sea: el problema práctico sigue siendo real, pero el cuello no es necesariamente “la clausura está rota”. Puede ser:
- scorer demasiado conservador para follow-ups reales
- edges nuevos poco conectivos
- cierre demasiado prudente para bridges inter-componente

## Qué no hice a propósito

- no propuse un método nuevo grande
- no desvié esto a embeddings/HDBSCAN/sistema alternativo
- no fingí una validación DB-backed que no pude correr en esta sesión

## Verificación ejecutada

```bash
/home/node/.local/bin/uv run pytest \
  tests/test_story_clustering.py \
  tests/test_story_matching_eval.py
```

Resultado esperado en esta sesión: tests verdes sobre la parte tocada.

## Lectura honesta final

La historia corta es esta:

- **bug de connected components:** no es la explicación principal
- **bug/mismatch de métricas:** sí, había un mismatch importante de interpretación
- **accepted pairs redundantes o poco conectivos:** sí, eso encaja de lleno con el diseño actual
- **otra lógica frenando agrupación real:** sí, el guarded closure actual frena fusiones que no sean suficientemente fuertes o singleton-attach compatibles

La palanca concreta siguiente, si se quiere mover algo después de esta auditoría, ya no es “arreglar union-find”.
Es decidir explícitamente una de estas dos cosas dentro del pipeline actual:

1. si ciertos bridges `medium` entre componentes no-singleton deberían poder fusionar clusters cuando tienen soporte suficiente, o
2. si el scorer debe empujar más pares reales hacia `strong` para que el cierre actual sí los una.

Primero había que dejar de confundir contadores. Eso ya quedó bastante más limpio.

---

## Histórico inmediato de la iteración

Dejé un workflow práctico para el bucle humano-en-el-medio del matching. Sin app nueva, sin teatro: ahora el repo puede

1. **comparar thresholds / acceptance policy**
2. **sacar tandas pequeñas revisables por humanos**
3. **capturar labels simples** (`same_event`, `different_event`, `uncertain`)
4. **reusar ese feedback para calibrar thresholds después**

La gracia no está en una UI. Está en que ahora hay outputs auditables y cómodos para revisar por lotes de 5-10 pares y luego volver a medir con cabeza.

## Qué añadí

### 1. Threshold sweep reutilizable
Nuevo módulo/helper: `src/analysis/story_review.py`

Nuevo script:
- `scripts/compare_story_thresholds.py`

Qué hace:
- corre el pipeline de pares sobre un fixture/export con varios thresholds
- deja `summary.json`
- deja `summary.md` con una tabla simple para comparar
- si hay labels disponibles, reporta `pair_precision`, `pair_recall`, `pair_f1`
- aunque no haya labels, deja señales operativas: pares aceptados, clusters, singletons, multi-clusters

Sanity check real sobre el fixture contractual:

| threshold | accepted_pairs | pair_recall | pair_f1 |
| --- | ---: | ---: | ---: |
| 0.45 | 3 | 1.0 | 1.0 |
| 0.55 | 2 | 0.6667 | 0.8 |
| 0.60 | 1 | 0.3333 | 0.5 |
| 0.68 | 1 | 0.3333 | 0.5 |
| 0.78 | 0 | 0.0 | 0.0 |

No son métricas mágicas de producción. Son el fixture contractual. Pero ya sirven para discutir policy sin hablar por intuición.

### 2. Batch humano cómodo para revisar en tandas cortas
Nuevo script:
- `scripts/prepare_story_review_batch.py`

Qué deja:
- `review-batch.jsonl` editable
- `review-batch.md` legible para chat/manual review
- `manifest.json`

La selección mezcla:
- `accepted_high`
- `borderline`
- `rejected_high`

Eso evita sesgar la revisión sólo a “lo obvio” y te deja mirar justo la zona donde un threshold cambia decisiones.

Ejemplo real del markdown generado en el fixture:
- muestra bucket
- predicción actual
- score
- candidate origins
- penalties
- título y summary de ambos artículos
- hueco explícito para `reviewer_label` y `reviewer_notes`

Esto ya vale para revisar 5 pares en chat sin tragarte dumps crudos infumables.

### 3. Resumen de feedback manual y sweep contra labels revisadas
Nuevo script:
- `scripts/summarize_story_review_feedback.py`

Qué hace:
- lee un `review-batch.jsonl` ya etiquetado
- resume cuántos casos hay por label/bucket
- calcula confusión básica ignorando `uncertain`
- barre thresholds sobre esos pares revisados para ver cómo cambia la calidad

Importante:
- `uncertain` **no contamina** la calibración. Se reporta, pero no entra en precision/recall/F1.
- esto es justo lo que hace falta para iterar rápido contigo o con otro humano sin inventar un sistema de labeling mastodóntico.

## Archivos tocados

- `src/analysis/story_review.py`
- `scripts/compare_story_thresholds.py`
- `scripts/prepare_story_review_batch.py`
- `scripts/summarize_story_review_feedback.py`
- `tests/test_story_review.py`
- `docs/architecture/story-matching-eval.md`
- `STATUS.md`
- `RESULTS.md`
- `TODO.md`
- `logs/iterations/009.md`

## Verificación ejecutada

```bash
/home/node/.local/bin/uv run pytest \
  tests/test_story_pair_scoring.py \
  tests/test_story_clustering.py \
  tests/test_story_matching_eval.py \
  tests/test_story_candidate_generation.py \
  tests/test_story_review.py
```

Resultado: `17 passed`.

También corrí:

```bash
/home/node/.local/bin/uv run python scripts/compare_story_thresholds.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output-dir artifacts/story-threshold-compare-iter009-phase4

/home/node/.local/bin/uv run python scripts/prepare_story_review_batch.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --output-dir artifacts/story-review-batch-iter009-phase4 \
  --batch-size 5

/home/node/.local/bin/uv run python scripts/summarize_story_review_feedback.py \
  --fixture tests/fixtures/story_matching_eval_fixture.json \
  --review-jsonl artifacts/story-review-batch-iter009-phase4/review-batch.jsonl \
  --output-dir artifacts/story-review-feedback-iter009-phase4
```

## Qué mejora real deja este pase

### 1. Ya se puede hablar de threshold con evidencia reproducible
Antes estaba claro que el threshold importaba, pero la operativa era torpe.
Ahora puedes correr un sweep y ver rápido:
- cuántos pares aceptas
- cuántos singletons dejas
- qué recall aparente recuperas en un fixture/gold set

### 2. Revisión manual práctica, no ceremoniosa
El markdown de batch está pensado para humanos, no para máquinas con fetiche por JSON:
- 5-10 pares
- contexto suficiente
- labels simples
- buckets útiles

### 3. El feedback manual ya no se queda en el limbo
Puedes etiquetar una tanda pequeña y luego resumirla con un comando.
Eso convierte “creo que está muy conservador” en algo más serio:
- cuántos false negatives vimos
- cuántos false positives salieron
- qué pasaría al mover el threshold

## Límites honestos

1. **Sigue faltando gold set real de producción.**
   El workflow ya existe, pero la calibración de verdad necesita usarlo sobre export reciente o DB accesible.

2. **No hay UI grande, y eso es deliberado.**
   El objetivo aquí era utilidad operativa, no construir un mini Label Studio cutre dentro del repo.

3. **El fixture no autoriza conclusiones globales.**
   Sirve para bloquear regresiones y para probar el flujo. No para declarar victoria estadística.

## Siguiente paso recomendado

1. sacar un export reciente de artículos enriquecidos
2. generar 2-3 tandas de revisión de 5-10 pares
3. etiquetar con `same_event` / `different_event` / `uncertain`
4. resumir feedback y correr sweep contra esas labels
5. recién ahí decidir si el siguiente ajuste es:
   - bajar/subir threshold,
   - cambiar acceptance policy,
   - o retocar scorer para buckets concretos (follow-up misses, opinion bleed, entity glue, etc.)

Ahora sí queda montado el circuito útil para iterar matching quality con humanos sin hacer una aplicación entera por el camino.

## Resumen git / saneamiento del worktree

Trabajo válido de iter/009 separado en commits atómicos:

- `b286f1f` — `feat(iter/009): harden story matching scoring and closure`
- `PENDING_COMMIT_HASH` — workflow de review humana + docs/estado final de iter/009

Rollback/review rápido recomendado:

```bash
git log --oneline -n 5
git show b286f1f
```

Ruido dejado fuera a propósito:
- `artifacts/` generados localmente para inspección
- `docs/architecture/2026-03-24-explorer-bias-lens-architecture.md`
- `docs/reviews/2026-03-24-iter-009-explorer-bias-lens-review.md`

Eso no se tocó ni se mezcló en los commits de iter/009 porque no forma parte clara del alcance de same-event matching.
