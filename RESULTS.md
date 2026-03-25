# RESULTS.md — iter/009 Phase 0 instrumentation + evaluation

## Executive summary

En este pase no toqué candidate generation v1, scorer v2 ni closure v2. Hice lo que hacía falta antes: **dejar una base reproducible para medir el matching actual y auditar por qué acepta o rechaza pares**.

Se añadieron:
- una capa de evaluación reutilizable (`src/analysis/story_eval.py`)
- un script de baseline (`scripts/evaluate_story_matching.py`)
- un script para bootstrap de gold manual (`scripts/bootstrap_story_gold_set.py`)
- un fixture/gold set inicial pequeño pero contractual (`tests/fixtures/story_matching_eval_fixture.json`)
- un test que fija el baseline actual (`tests/test_story_matching_eval.py`)
- documentación específica (`docs/architecture/story-matching-eval.md`)

La baseline reproducible que sí queda cerrada en repo muestra justo el patrón que sospechábamos: **el sistema actual mantiene precisión en un rewrite cercano, pero pierde recall en follow-ups legítimos**.

---

## Hallazgos principales

### 1. El clustering de historias no usa la capa semántica de Explorer
Evidencia:
- `scripts/build_story_clusters.py` llama a `ClusterPipeline.build_clusters()`
- `src/semantic/analyze.py` y `src/semantic/dbstore.py` sirven a embeddings/projections/HDBSCAN/Explorer
- `docs/architecture/semantic-pipeline.md` incluso lo dice explícitamente: semantic explorer y story clustering responden preguntas distintas

Implicación:
- si hoy hay infragrupar, la causa principal está en `src/analysis/pipeline.py`, no en HDBSCAN.

### 2. El sistema ya está planteado como pairwise matching + graph closure
Eso es bueno. No hay que tirar el repo.

Evidencia:
- `score_pair()` calcula features por par y devuelve `StoryClusterMemberReason`
- `_connected_components()` añade candidatos con guardrails de soporte y riesgo
- tests existentes (`tests/test_story_pair_scoring.py`, `tests/test_story_clustering.py`) validan justo esa lógica

Implicación:
- la mejora natural es evolucionar esa arquitectura, no sustituirla por topic clustering opaco.

### 3. Las features actuales son demasiado flojas para capturar mismo evento con rewrite real
Evidencia:
- `heuristic_enrichment()` genera `key_phrases` casi sólo desde el título troceado por puntuación
- `title_similarity()` usa `SequenceMatcher`
- la feature llamada `semantic_similarity` es realmente Jaccard sobre keyphrases/entities, no embeddings

Implicación:
- con titulares distintos entre medios, el sistema pierde recall aunque el evento sea el mismo.

### 4. La selección de artículos a clusterizar probablemente deja fuera pares válidos
Evidencia:
- `_load_enriched_articles()` recorta por recency con `order_by(...).limit(limit)`
- no replica el source balancing del enrichment
- no hace candidate expansion por entidades/tags/vecinos

Implicación:
- parte del under-grouping puede ocurrir antes incluso del scoring.

### 5. El cierre conservador protege precisión, pero parte clusters reales
Evidencia:
- edges `risky_bridge_pair` con score < 0.78 ni entran al grafo
- clusters >1 piden soporte múltiple o scores muy altos
- tests ya codifican protección explícita contra bridges falsos

Implicación:
- follow-ups legítimos, outlets minoritarios o rewrites con un solo pivot fuerte pueden quedarse fuera.

### 6. Hay inconsistencia operativa de thresholds
Evidencia:
- `scripts/build_story_clusters.py` default `--score-threshold 0.68`
- `scripts/run_stories_refresh.sh` usa `SCORE_THRESHOLD=0.45`

Implicación:
- comparar runs manuales vs scheduler puede inducir diagnósticos basura.

---

## Causas más probables de infragrupar

Ordenadas por probabilidad/impacto:

1. **candidate recall insuficiente** por recorte simple de artículos clusterizados
2. **keyphrases pobres** y demasiado dependientes del titular
3. **title similarity superficial** incapaz de capturar parafraseo cross-outlet
4. **penalizaciones y closure conservadores** que rompen follow-ups o attaches por pivot único
5. **variabilidad de thresholds operativos** que confunde evaluación
6. **sin truth set ni métricas**, lo que impide calibrar con criterio

---

## Viabilidad de enfoques evaluados

### Enfoque: embeddings/HDBSCAN como nuevo core de story grouping
- Viabilidad técnica: alta
- Fit con repo: bajo
- Recomendación: **no**

Motivo: la capa semántica actual sirve para Explorer y vecindad, no para mismo evento. Same-event necesita tiempo, actores y acción, no sólo proximidad temática.

### Enfoque: candidate generation + pair scoring + graph closure
- Viabilidad técnica: muy alta
- Fit con repo: muy alto
- Recomendación: **sí, dirección principal**

### Enfoque: mejorar features del scorer actual
- Viabilidad: muy alta
- ROI: alto
- Recomendación: **sí, pase temprano**

### Enfoque: separar near-duplicate vs same-event
- Viabilidad: alta
- ROI: alto
- Recomendación: **sí, como framing y reglas/métricas primero**

### Enfoque: learned reranker / cross-encoder / LLM pair judge
- Viabilidad: media
- ROI actual: incierto
- Recomendación: **defer** hasta tener baseline y dataset

---

## Recomendación clara

### Framing recomendado
Tratar el problema como **same-event matching híbrido**, no como simple clustering temático.

### Arquitectura recomendada
1. candidate generation de alta recall
2. pair scorer v2 con mejores señales textuales/event-aware
3. graph closure auditable y menos miope
4. semantic neighbors/embeddings sólo como señal auxiliar o expansión de recall

### Primeras implementaciones de mayor valor
1. instrumentación + dataset de evaluación
2. candidate generation
3. pair scorer v2
4. closure v2

---

## Métricas recomendadas

### Pair-level
- precision
- recall
- F1
- candidate recall@k

### Cluster-level
- pairwise cluster F1 o B-cubed
- singleton rate
- avg cluster size
- % clusters multi-source
- split rate en eventos etiquetados
- false merge count en muestra auditada

### Operativas
- artículos comparados por seed
- candidatos por origen (tag/entity/lexical/semantic)
- artículos excluidos por `limit`
- artículos sin candidatos
- artículos rechazados por `risky_bridge_only`

---

## Riesgos

### Riesgo 1: subir recall y comerse merges falsos
Mitigación:
- candidate stage amplia recall, pero scorer/closure conservan la decisión final
- medir false merges explícitamente

### Riesgo 2: complejidad prematura
Mitigación:
- no meter reranker/LLM hasta exprimir baseline feature-based

### Riesgo 3: ruido en entidades/tags
Mitigación:
- usar salience y no sólo overlap bruto
- auditar fuentes de candidates por feature origin

### Riesgo 4: seguir sin saber si mejora de verdad
Mitigación:
- crear gold set pequeño y estable antes de tocar demasiado

---

## Próximos pases recomendados

### Pase 1 — instrumentation/eval subagent
Debe dejar:
- script de evaluación
- dump de pair features
- gold set inicial
- baseline numbers

### Pase 2 — backend matching subagent
Debe dejar:
- candidate generation v1
- tests de candidate recall / blocking

### Pase 3 — backend scoring subagent
Debe dejar:
- scorer v2
- calibración inicial
- tests de follow-up / rewrite / false glue

### Pase 4 — backend closure subagent
Debe dejar:
- closure v2
- mejores diagnostics de exclusión/attach

### Pase 5 — optional ML/research subagent
Sólo si el baseline medido se queda corto.

---

## Repo-specific notes worth keeping

- Los artefactos previos de `PLAN.md` y `RESULTS.md` estaban contaminados con trabajo de Explorer bias lens y no correspondían a iter/009 same-event matching.
- El repo ya tiene una distinción conceptual correcta entre Stories y Explorer; conviene preservarla.
- El detalle más engañoso del código actual es el nombre `semantic_similarity` dentro del scorer de stories: hoy no representa embeddings semánticos reales.
- El sistema actual no está roto conceptualmente; está subinstrumentado y probablemente demasiado conservador para recall.
