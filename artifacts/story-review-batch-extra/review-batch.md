# Story matching review batch

Labels válidos: `same_event`, `different_event`, `uncertain`.

## Pair 1: 1 ↔ 2
- bucket: `accepted_high`
- predicted: `same_event` | score: `0.7736` | candidate_rank: `1`
- candidate_origins: lexical_neighbor, shared_entity, shared_tag, temporal_window
- penalties: none
- risky_bridge_pair: `False`
- left:
  - [elpais] 2026-03-18T10:00:00+00:00
  - title: Illa anuncia un acuerdo con ERC sobre presupuestos
  - summary: El Govern anuncia un pacto presupuestario con ERC tras varios días de negociación.
- right:
  - [elmundo] 2026-03-18T13:00:00+00:00
  - title: El Govern sella con ERC las cuentas catalanas tras una larga negociación
  - summary: El ejecutivo catalán cierra el acuerdo de presupuestos con ERC.
- reviewer_label: ``
- reviewer_notes: 

## Pair 2: 1 ↔ 4
- bucket: `borderline`
- predicted: `different_event` | score: `0.6007` | candidate_rank: `1`
- candidate_origins: shared_entity, shared_tag, temporal_window
- penalties: none
- risky_bridge_pair: `False`
- left:
  - [elpais] 2026-03-18T10:00:00+00:00
  - title: Illa anuncia un acuerdo con ERC sobre presupuestos
  - summary: El Govern anuncia un pacto presupuestario con ERC tras varios días de negociación.
- right:
  - [abc] 2026-03-18T16:00:00+00:00
  - title: Opinión: el peaje político de Illa por pactar con ERC
  - summary: Una columna sobre el coste político del acuerdo.
- reviewer_label: ``
- reviewer_notes: 

## Pair 3: 2 ↔ 4
- bucket: `borderline`
- predicted: `different_event` | score: `0.5970` | candidate_rank: `2`
- candidate_origins: shared_entity, shared_tag, temporal_window
- penalties: none
- risky_bridge_pair: `False`
- left:
  - [elmundo] 2026-03-18T13:00:00+00:00
  - title: El Govern sella con ERC las cuentas catalanas tras una larga negociación
  - summary: El ejecutivo catalán cierra el acuerdo de presupuestos con ERC.
- right:
  - [abc] 2026-03-18T16:00:00+00:00
  - title: Opinión: el peaje político de Illa por pactar con ERC
  - summary: Una columna sobre el coste político del acuerdo.
- reviewer_label: ``
- reviewer_notes: 

## Pair 4: 1 ↔ 3
- bucket: `borderline`
- predicted: `different_event` | score: `0.5871` | candidate_rank: `2`
- candidate_origins: shared_entity, shared_tag, temporal_window
- penalties: none
- risky_bridge_pair: `False`
- left:
  - [elpais] 2026-03-18T10:00:00+00:00
  - title: Illa anuncia un acuerdo con ERC sobre presupuestos
  - summary: El Govern anuncia un pacto presupuestario con ERC tras varios días de negociación.
- right:
  - [eldiario] 2026-03-21T09:00:00+00:00
  - title: ERC exige nuevas condiciones a Illa dos días después del pacto presupuestario
  - summary: Las conversaciones sobre el acuerdo siguen abiertas y ERC reclama ajustes.
- reviewer_label: ``
- reviewer_notes: 
