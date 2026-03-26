# RESULTS.md — iter/010 implementer pass

## Resumen breve

El cuello de botella real estaba en **guarded closure**, no en Stories read-side.

Con evidencia reproducible:
- el grafo raw puede contener **5 artículos** conectados por accepted edges medium limpios
- `_preserve_medium_components(...)` sólo permitía rescatar componentes de tamaño **2-3**
- cuando el componente raw era de **5**, el cierre lo dejaba caer
- el attach posterior sólo conseguía recomponer el **seed pair** y dejaba el resto como singletons cuando sus soportes estaban en el rango bajo-medium (~0.55)
- si eso se persiste, `cluster_members` y por tanto Stories acaban mostrando **2 miembros**, mientras Explorer puede seguir enseñando un vecindario semántico más ancho

Traducción: la pérdida ocurre en el paso **raw component -> guarded closure final components**. Stories no estaba “recortando”; estaba leyendo fielmente un resultado ya encogido.

## Caso congelado / traza del fallo

Reproducción exacta protegida ahora en `tests/test_story_clustering.py::test_guarded_components_preserve_coherent_medium_only_chain_of_five`.

IDs trazados en la regresión: `1,2,3,4,5`

Accepted edges relevantes:
- `1-2` score `0.56`
- `2-3` score `0.55`
- `3-4` score `0.55`
- `4-5` score `0.55`

Todos los edges del caso son:
- no risky bridge
- no `secondary_form_pair`
- sin `entity_glue_penalty`, `late_story_drift_penalty` ni `secondary_form_penalty`
- `days_delta <= 1`
- con señal no trivial de tags/keyphrases

Traza end-to-end del patrón:
- candidate / accepted-edge stage: **sí pasa**; existen edges aceptados entre los 5 ids
- raw connected components: `[[1, 2, 3, 4, 5]]`
- guarded closure **antes del fix**: `[[1, 2], [3], [4], [5]]`
- guarded closure **después del fix**: `[[1, 2, 3, 4, 5]]`
- persistencia: al persistir, `cluster_members` reflejará el resultado de closure; por eso el loss stage verdadero está antes de DB/read-side
- Stories read-side: consume `cluster_members`, así que no era el culpable primario
- Explorer: puede seguir mostrando más vecinos por embeddings, lo que hacía visible el desajuste

## Causa raíz exacta

En `src/analysis/pipeline.py`, `_audit_medium_component(...)` tenía este guardrail:
- rechazar cualquier raw component medium-only con tamaño `> 3`

Ese límite era demasiado estrecho para componentes medium-only limpios y coherentes de tamaño 4-5.

Cuando eso ocurría:
1. el raw component de 5 no se preservaba como bloque
2. el attach tardío evaluaba singletons contra clusters ya formados
3. con soportes en torno a `0.55`, sólo sobrevivía el emparejamiento inicial más fuerte
4. el resto se quedaba fuera

Eso produce exactamente el patrón “Explorer parece mostrar ~5 del mismo barrio, Stories sólo 2”.

## Fix aplicado

Cambio mínimo y acotado en `src/analysis/pipeline.py`:
- ampliar preservación medium-only de tamaño máximo `3` a tamaño máximo `5`
- mantener el fix **bounded** con umbrales algo más estrictos para componentes `4-5` en default mode:
  - tamaño `<= 3`: sigue igual (`mean >= 0.54`, `best >= 0.56`)
  - tamaño `4-5`: ahora exige `mean >= 0.55`, `best >= 0.56`
- no se tocaron los guardrails críticos:
  - no risky bridges
  - no `secondary_form_pair`
  - no `entity_glue_penalty`
  - no `late_story_drift_penalty`
  - no `secondary_form_penalty`
  - `days_delta <= 3`
  - sigue requiriendo señal no trivial de tags/keyphrases

O sea: no abrí la puerta a merges blandos generales. Quité un límite arbitrario que estaba rompiendo componentes coherentes un poco más grandes.

## Regresión añadida

Nuevo test:
- `tests/test_story_clustering.py::test_guarded_components_preserve_coherent_medium_only_chain_of_five`

Lo que prueba:
- el componente raw de 5 existe
- el cierre final ya no lo colapsa a 2 + singletons
- el count transition problem queda bloqueado con una prueba explícita

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
- `40 passed`

## Limitación operativa encontrada

La base Postgres local del repo no estaba accesible durante esta iteración:
- `127.0.0.1:5433` → `connection refused`

Eso impidió extraer un tuple vivo desde `story_clusters` / `cluster_members` del entorno local.

Aun así, el bottleneck exacto sí quedó probado de forma mecánica y auditable en el propio pipeline con una regresión que reproduce el patrón de pérdida `5 -> 2` en el stage correcto.

## Git / alcance

Cambios de código:
- `src/analysis/pipeline.py`
- `tests/test_story_clustering.py`

Cambios de documentación/estado:
- `RESULTS.md`
- `STATUS.md`
- `logs/iterations/010.md`

## Veredicto honesto

El problema no era que Stories escondiese miembros ya persistidos. El problema era más arriba y más feo: **guarded closure estaba tirando por la borda componentes medium-only coherentes de tamaño 4-5 por un cap arbitrario de tamaño 3**.

Eso ya no pasa para el patrón limpio y acotado que reproduje.