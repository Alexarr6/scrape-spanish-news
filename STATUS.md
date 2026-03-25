# STATUS.md

- State: DONE
- Iteration: iter/009
- Focus: saneamiento del worktree + commits atómicos del trabajo válido de iter/009
- Notes:
  - La auditoría del pipeline actual apunta a **métrica ambigua + cierre deliberadamente conservador**, no a un bug simple de union-find/connected-components.
  - `accepted_pair_count` cuenta todos los edges aceptados por score/threshold, pero el cierre final **no usa todos esos edges igual**: construye componentes base sólo con edges `strong` y usa muchos `medium` sólo para attach de singletons.
  - Consecuencia: bajar threshold puede inflar bastante `accepted_pairs` sin mover apenas `cluster_count`, especialmente si los nuevos edges son redundantes dentro de componentes ya conectados o puentes `medium` entre componentes no-singleton que el cierre no fusiona.
  - Se añadieron métricas explícitas para dejar esto visible en runtime: `raw_component_count`, `guarded_cluster_count`, `accepted_strong_pair_count`, `accepted_medium_pair_count`, `singleton_count`, `closure_decision_counts`, etc.
  - Se añadió test que fija el comportamiento clave: el grafo crudo puede colapsar a un solo componente mientras el cierre guardado conserva dos clusters separados.
  - Validación local ejecutada con `uv run pytest tests/test_story_clustering.py tests/test_story_matching_eval.py`.
  - El trabajo válido de iter/009 quedó separado en commits atómicos en `iter/009`; el ruido ajeno (`artifacts/`, docs viejas de explorer bias lens) quedó fuera.
  - Commits útiles del saneamiento: `b286f1f` (matching/closure hardening) y el commit de workflow/docs que cierra este saneamiento.
  - Limitación honesta: no pude reproducir la DB local del usuario en este runtime (`127.0.0.1:5433` rechazando conexión), así que el diagnóstico fino sale del código/tests y no de una corrida DB-backed en esta sesión.
