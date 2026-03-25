# STATUS.md

- State: PHASE_0_INSTRUMENTATION_DONE
- Iteration: iter/009
- Focus: same-event matching instrumentation + evaluation baseline
- Notes:
  - Se dejó un scaffold repo-appropriate para evaluar el matching actual sin reescribir el pipeline: `src/analysis/story_eval.py`, `scripts/evaluate_story_matching.py`, `scripts/bootstrap_story_gold_set.py`.
  - El baseline reproducible inicial vive en `tests/fixtures/story_matching_eval_fixture.json` y queda bloqueado por `tests/test_story_matching_eval.py`.
  - Baseline del fixture incluido con threshold 0.68: pair precision 1.0, pair recall 0.3333, pair F1 0.5, cluster pairwise recall 0.3333; patrón claro de miss en follow-up legítimo.
  - Se generan dumps auditables por par en JSONL (`pair-artifacts.jsonl`) y un bootstrap de pares para etiquetado manual (`manual-gold-candidates.jsonl`).
  - Límite honesto de este pase: no se pudo correr baseline sobre DB real desde este entorno porque el runtime del subagente no traía el stack Python/deps operativo del repo; se dejó el andamiaje y un fixture contractual reproducible en vez de inventarse números de producción.
