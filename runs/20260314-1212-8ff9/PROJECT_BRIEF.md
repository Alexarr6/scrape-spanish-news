# PROJECT_BRIEF.md

## 1) Nombre del proyecto
Spain News Scraper — Fuente 20minutos (fase inicial)

## 2) Objetivo (1-2 frases)
Añadir 20minutos como nueva fuente al sistema multi-medio respetando las reglas ya establecidas (core+adapters, baseline canónico, no-regresión, guardrails, commits atómicos).

## 3) Contexto técnico
- Repo/path: `/home/node/.openclaw/workspace/repos/spain-news-bias-scraper/runs/20260314-1212-8ff9`
- Stack: Python 3 CLI
- Arquitectura: core compartido + adapter por medio
- Git: rama `feat/spain-news-bias-scraper-20260314-1212-8ff9`

## 4) Inputs / Outputs
- Inputs:
  - Fuente: 20minutos (España/política/nacional relacionadas)
  - Fecha objetivo por CLI
- Outputs:
  - `data/news_20minutos_<date>.json`
  - opcional `data/news_20minutos_<date>.csv`
  - métricas en `logs/*`

## 5) In scope
- [x] Adapter `20minutos` reutilizando código común
- [x] Integración CLI multi-source consistente
- [x] Filtro por fecha (UTC)
- [x] Validación de no-regresión en fuentes existentes

## 6) Out of scope
- [x] Sesgo/análisis editorial
- [x] Infra avanzada
- [x] scraping autenticado

## 7) Criterios de aceptación
- [x] `--source 20minutos` operativo
- [x] Conteo >0 para fecha objetivo con titulares relevantes
- [x] Formato JSON/CSV homogéneo
- [x] No-regresión razonable en fuentes previas
- [x] Commits atómicos por fase

## 8) Tests / verificaciones
- [x] help + tests
- [x] corrida 20minutos por fecha
- [x] corrida canónica comparativa fuentes previas

## 9) Entrega esperada
- adapter + evidencias en RESULTS
- resumen git + rollback

## 10) Riesgos
- cambios de estructura o feeds de 20minutos
- ruido de enlaces no relevantes
