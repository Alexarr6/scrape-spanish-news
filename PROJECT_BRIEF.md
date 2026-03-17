# PROJECT_BRIEF.md

## 1) Nombre del proyecto
Spain News Bias Scraper — análisis de cobertura vacía de `article_text` en El Mundo

## 2) Objetivo (1-2 frases)
Analizar por qué una gran parte de los artículos de **El Mundo** están llegando con `article_text` vacío en la salida y persistencia del scraper. Diseñar un plan técnico concreto para diagnosticar la causa raíz y proponer una solución verificable y segura.

## 3) Contexto técnico
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`
- Stack principal: Python 3 + scraper multi-fuente + persistencia/API
- Evidencia inicial observada en datos locales del repo: `data/sched_elmundo_2026-03-16.json` muestra ~82% de artículos con `article_text` vacío, mientras otras fuentes del mismo día salen casi completas.
- Restricción operativa: en este host no hay Docker disponible; el análisis debe apoyarse en código, fixtures, tests y fetches HTTP normales si hacen falta.

## 4) Inputs / Outputs
- Inputs: adapter de El Mundo, estrategia de extracción de texto actual, tests existentes, outputs JSON recientes, y cualquier patrón anti-bot / lazy-load / JSON-LD / paywall / rendering detectado.
- Outputs: diagnóstico de causa raíz, hipótesis priorizadas, plan por fases, verificación reproducible y recomendación de implementación.

## 5) In scope
- [x] Medir y describir el fallo en El Mundo con evidencia concreta
- [x] Revisar el adapter y pipeline de extracción de `article_text`
- [x] Comparar El Mundo con una o dos fuentes que sí funcionan
- [x] Proponer solución técnica y estrategia de validación
- [x] Definir riesgos (paywall, HTML dinámico, bloques anti-bot, cambios de markup)

## 6) Out of scope (do-not)
- [x] No implementar aún cambios de producción sin aprobación humana
- [x] No rehacer todos los adapters si el problema está concentrado en El Mundo
- [x] No meter browser automation pesada salvo justificación brutal
- [x] No tocar la base de datos en producción ni hacer cambios destructivos

## 7) Criterios de aceptación
- [x] El análisis identifica causa raíz o reduce el problema a 1-2 hipótesis fuertes con evidencia
- [x] El plan propone una solución concreta y incremental
- [x] La verificación define cómo medir mejora en porcentaje de `article_text` no vacío
- [x] El handoff deja claro qué tocar, cómo probarlo y qué riesgos vigilar

## 8) Tests / verificaciones requeridas
- [x] Revisar outputs recientes (`data/*.json`) para cuantificar el problema
- [x] Revisar adapter/tests de El Mundo y extracción común
- [x] Comparar con una fuente sana (por ejemplo ABC o El País)
- [x] Dejar comandos verificables para una futura implementación

## 9) Entrega esperada
- Formato: actualización de `PLAN.md` + `STATUS.md` con diagnóstico y plan
- Evidencias mínimas: ratio de vacíos por fuente, posibles causas, estrategia de fix, pruebas propuestas

## 10) Riesgos / restricciones
- Seguridad: no añadir scraping agresivo ni bypasss dudosos
- Datos: evitar falsos positivos rellenando `article_text` con basura o resúmenes incompletos
- Operación: el markup del medio puede variar por secciones o por presencia de paywall
- Calidad: un fix debe mejorar cobertura sin degradar otras fuentes
