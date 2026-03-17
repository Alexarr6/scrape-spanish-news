# TASK_CONTRACT.md

## Objective
Diagnosticar por qué El Mundo produce un porcentaje muy alto de `article_text` vacío y dejar un plan técnico accionable para corregirlo sin romper el resto del scraper.

## Technical Context
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- Señal actual: `data/sched_elmundo_2026-03-16.json` tiene 17 artículos, 14 con `article_text` vacío (~82.4%)
- Otras fuentes del mismo día salen bien, lo que apunta a un problema específico de source adapter / extracción / markup en El Mundo
- No asumir Docker/browser automation; preferir diagnóstico reproducible con código, fixtures, tests y fetches ligeros

## Scope
- [x] Cuantificar el problema y describirlo con evidencia
- [x] Inspeccionar adapter/pipeline de El Mundo y puntos comunes de extracción de texto
- [x] Comparar comportamiento con una fuente sana
- [x] Proponer plan de fix incremental con verificación
- [x] Documentar riesgos y decisiones humanas

## Non-goals
- [x] No implementar aún el fix final sin aprobación humana
- [x] No introducir Selenium/Playwright salvo necesidad demostrada
- [x] No alterar adapters sanos por intuición
- [x] No hacer scraping agresivo ni saltos dudosos de protección

## Acceptance Criteria (checklist)
- [x] El planner entrega un diagnóstico o 1-2 hipótesis fuertes con evidencia suficiente
- [x] `PLAN.md` incluye fases claras para instrumentar, corregir y validar
- [x] Se definen métricas de éxito (p. ej. reducción sustancial del ratio de vacíos en El Mundo)
- [x] El handoff al implementer indica archivos probables, pruebas y límites

## Verification
Comandos o checks verificables:
```bash
# Cuantificar cobertura actual por fuente
python3 - <<'PY'
import json,glob,os
for path in sorted(glob.glob('data/sched_*_2026-03-16.json')):
    data=json.load(open(path))
    arts=data if isinstance(data,list) else data.get('articles',[])
    total=len(arts)
    empty=sum(1 for a in arts if not (a.get('article_text') or '').strip())
    print(os.path.basename(path), total, empty, round(empty/total, 3) if total else None)
PY

# Revisar tests y adapters relacionados con El Mundo
rg -n "elmundo|article_text|articleBody|keywords|json-ld" src tests
```

## Delivery Expectations
- Artefactos esperados: `PLAN.md` actualizado + `STATUS.md` en `PLANNING_DONE`
- Reporte: causa raíz / hipótesis, plan por fases, riesgos, comandos de validación, primer paso exacto de implementación

## Safety Constraints
- No secretos en repo/logs
- No cambios destructivos sin aprobación
- No browser automation pesada ni bypass anti-bot sin aprobación explícita
- Mantener el fix acotado y reversible
