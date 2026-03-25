# STATUS.md

- State: PHASE_1_CANDIDATE_GENERATION_V1_DONE
- Iteration: iter/009
- Focus: same-event matching candidate generation v1
- Notes:
  - `ClusterPipeline.build_clusters()` ya no compara all-pairs dentro del slice reciente; ahora pasa por una stage explícita de candidate generation v1.
  - Candidate generation v1 combina señales auditables y acotadas: `temporal_window`, `shared_tag`, `shared_entity`, `lexical_neighbor`.
  - Cada `PairScoreArtifact` ahora expone `candidate_origins` y `candidate_rank` para diagnosticar de dónde salió el par y con qué prioridad entró.
  - `ClusterRebuildMetrics` agrega `candidate_origin_counts` y `candidate_overflow_counts` para ver cobertura/caps por origen.
  - `src/analysis/story_eval.py` ya calcula `candidate_recall_summary` (recall@k sobre pares positivos etiquetados) usando el rank de candidate generation.
  - Cobertura de tests añadida en `tests/test_story_candidate_generation.py`; validación local ejecutada con `uv run pytest` sobre los tests de story matching relevantes (`11 passed`).
  - Límite honesto de este pase: sigue faltando medir sobre DB real o export enriquecido reciente; el recall@k serio queda listo pero depende de labels reales.
