# TASK_CONTRACT.md

## Objective
Integrar 20minutos como nueva fuente en el scraper multi-medio manteniendo arquitectura limpia, reutilización máxima y no-regresión de capacidades existentes.

## Technical Context
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper/runs/20260314-1212-8ff9`
- Stack/runtime: Python 3 CLI, core+adapters

## Scope
- [x] añadir adapter 20minutos
- [x] integrar `--source 20minutos`
- [x] mantener pipeline común y guardrails
- [x] validar no-regresión

## Non-goals
- [x] no sesgo
- [x] no infra nueva

## Acceptance Criteria
- [x] comando con 20minutos funciona por fecha
- [x] outputs estándar y métricas homogéneas
- [x] fuentes existentes sin degradación fuerte no explicada

## Verification
```bash
python3 -m src.main --help
python3 -m unittest discover -s tests -v
python3 -m src.main --source 20minutos --date YYYY-MM-DD --out data/news_20minutos_YYYY-MM-DD.json
python3 -m src.main --source elpais --date YYYY-MM-DD --out data/reg_elpais_YYYY-MM-DD.json
python3 -m src.main --source elmundo --date YYYY-MM-DD --out data/reg_elmundo_YYYY-MM-DD.json
python3 -m src.main --source abc --date YYYY-MM-DD --out data/reg_abc_YYYY-MM-DD.json
python3 -m src.main --source lavanguardia --date YYYY-MM-DD --out data/reg_lavanguardia_YYYY-MM-DD.json
```

## Delivery Expectations
- adapter + integración + resultados comparativos
- commits atómicos por fase

## Safety Constraints
- no secretos / no acciones destructivas / respetar guardrails
