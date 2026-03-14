# RESULTS.md

## Resumen de entrega
Integración de **La Vanguardia** como cuarta fuente en arquitectura core+adapters, con discovery en cascada **RSS → sitemap → HTML fallback**, whitelist inicial centrada en España/política/nacional, CSV opcional (mismo stack), y hard cap runtime por defecto en CLI de **180s**.

## Baseline previo obligatorio
Ejecutado antes de implementar adapter:

```bash
python3 -m src.main --help
python3 -m unittest discover -s tests -v
```

Estado baseline: OK.

## Cambios realizados
- Adapter nuevo: `src/adapters/lavanguardia.py`
  - discovery por capas: RSS, sitemap, HTML fallback
  - whitelist inicial: rutas/slug con `espana`, `politica`, `nacional`
  - fallback HTML limitado a 5 páginas
- Integración CLI:
  - `--source lavanguardia` añadido al registry
  - defaults guardrails: `--max-articles-to-extract=100`, `--max-runtime-seconds=180`
- Tests:
  - nuevo `tests/test_lavanguardia_adapter.py`
  - `tests/test_registry.py` actualizado para incluir `lavanguardia`

## Evidencias de verificación

### 1) Help + tests
```bash
python3 -m src.main --help
python3 -m unittest discover -s tests -v
```
Resultado: OK, 8 tests en verde.

### 2) Validación comparativa por fecha específica (2026-03-13)
Comandos ejecutados:
```bash
python3 -m src.main --source lavanguardia --date 2026-03-13 --out data/news_lavanguardia_2026-03-13.json --metrics-out logs/lavanguardia_metrics.json
python3 -m src.main --source lavanguardia --date 2026-03-13 --out data/news_lavanguardia_2026-03-13.csv --metrics-out logs/lavanguardia_metrics_csv.json
python3 -m src.main --source elpais --date 2026-03-13 --out data/reg_elpais_2026-03-13.json --metrics-out logs/reg_elpais_metrics.json
python3 -m src.main --source elmundo --date 2026-03-13 --out data/reg_elmundo_2026-03-13.json --metrics-out logs/reg_elmundo_metrics.json
python3 -m src.main --source abc --date 2026-03-13 --out data/reg_abc_2026-03-13.json --metrics-out logs/reg_abc_metrics.json
```

Conteos finales:
- `lavanguardia`: **29** artículos (JSON + CSV generado)
- `elpais`: **17** artículos
- `elmundo`: **27** artículos
- `abc`: **17** artículos

No-regresión rápida fuentes existentes: **OK** (elpais/elmundo/abc ejecutan y exportan).

### 3) Muestra de titulares
- lavanguardia:
  - ¿Sánchez está “jodío”?, por Isabel Garcia Pagan
  - Fernández Díaz y Ábalos, en el banquillo: una singular coincidencia
  - Feijóo pide una victoria “contundente” para evitar el bloqueo de Abascal
- elpais:
  - ‘Torrente presidente’: soez, excesiva y por momentos muy divertida
  - Estados Unidos autoriza a Venezuela a vender fertilizantes ante la escasez global por la crisis de Irán
- elmundo:
  - El Gobierno recoloca en secreto en Adif al mismo cargo al que cesó por la crisis de Rodalies
  - El 'cambio de cara' de Vox: una pasarela de aliados de Abascal para blindarse el 15-M
- abc:
  - Bolaños amplía el plazo de candidaturas a juez del TEDH... un día
  - Prisión sin fianza para el detenido por provocar un incendio en el que murieron tres mujeres en Miranda de Ebro

## Resumen git (commits atómicos por fase)
1. `320cae6` — `docs(plan): baseline checkpoints + restore core scraper scaffold`
2. `00b018a` — `feat(adapter): add lavanguardia adapter with rss+sitemap+html fallback`
3. `2d97524` — `feat(cli): wire lavanguardia source and enforce runtime guardrails`

## Rollback
Rollback completo de esta integración:
```bash
git revert --no-edit 2d97524 00b018a 320cae6
```

Rollback parcial (solo lavanguardia):
```bash
git revert --no-edit 2d97524 00b018a
```

## Pendientes / limitaciones
- Los endpoints públicos de LV (RSS/sitemap/HTML) pueden variar; el adapter ya degrada por capas pero conviene monitorizar estabilidad.
- Whitelist inicial deliberadamente conservadora para minimizar ruido y desbloquear gates.
