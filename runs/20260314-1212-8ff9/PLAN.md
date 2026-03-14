# PLAN.md

## 1) Resumen ejecutivo
Integrar **20minutos** como nueva fuente del scraper multi-medio sin romper comportamiento existente, respetando arquitectura **core + adapters** y guardrails de ejecución.

La implementación debe seguir un flujo incremental: (a) discovery de endpoints fiables de 20minutos, (b) adapter 20minutos sobre pipeline común, (c) integración CLI multi-source, (d) validación comparativa contra baseline canónico de fuentes previas.

**Definición de éxito:**
- `--source 20minutos` funciona por fecha y devuelve >0 noticias relevantes en fecha válida.
- Salida homogénea (JSON y opcional CSV) con el mismo contrato de campos que el resto.
- No-regresión observable en `elpais`, `elmundo`, `abc`, `lavanguardia`.
- Cambios en commits atómicos por fase (rollback claro).

---

## 2) Supuestos explícitos
1. El código productivo vive en el repo base (`/home/node/.openclaw/workspace/repos/spain-news-bias-scraper`) y este run workspace contiene la planificación/evidencia.
2. Existe ya un patrón de adapter reutilizable (por ejemplo, módulos por fuente y utilidades comunes de parsing/filtro/output).
3. El CLI ya soporta `--source`, `--date`, `--out`; añadir fuente nueva debe ser extensión declarativa, no refactor masivo.
4. Fecha de filtrado se interpreta en UTC (como exige contrato).
5. Si RSS no cubre todas las noticias de interés, se permite fallback controlado a sitemap/HTML sin romper guardrails.
6. No se usarán secretos, sesiones autenticadas ni bypasses anti-bot agresivos.

---

## 3) Fases numeradas

### Fase 0 — Preflight + baseline canónico (obligatoria)
**Objetivo**
Asegurar entorno reproducible y congelar baseline para comparar no-regresión.

**Tareas (checklist)**
- [ ] Confirmar rama activa y estado limpio (`git status`, `git branch --show-current`).
- [ ] Descubrir comandos reales de proyecto (si existen `Makefile`, `README`, `pyproject.toml`).
- [ ] Ejecutar preflight mínimo:
  - [ ] `python3 -V`
  - [ ] `python3 -m src.main --help` (o comando equivalente detectado)
  - [ ] `python3 -m unittest discover -s tests -v` (si hay suite)
- [ ] Definir **fecha canónica** para comparación (recomendada: día reciente con cobertura en todas las fuentes).
- [ ] Generar baseline canónico de fuentes existentes (`elpais`, `elmundo`, `abc`, `lavanguardia`) con outputs versionados en `data/` y métricas en `logs/`.
- [ ] Guardar snapshot comparativo inicial (conteos + validación de esquema por fuente).

**Dependencias**
- Ninguna.

**Riesgos**
- Comandos documentados no coinciden con repo real.
- Alguna fuente base devuelve 0 por fecha elegida.

**Mitigación**
- Paso de descubrimiento de comandos antes de ejecutar batería completa.
- Definir hasta 3 fechas candidatas (D-1, D-2, D-3) y fijar la primera con cobertura estable.

**Verificación/tests**
- Help del CLI operativo.
- Tests existentes en verde (o fallo preexistente documentado como baseline defect).
- Tabla baseline creada: `{fuente, fecha, n_items, campos_faltantes, errores}`.

**Done criteria**
- Baseline canónico persistido y referenciado en `RESULTS.md`.
- Fecha canónica fijada para toda la validación posterior.

**commit when done:** `chore(baseline): freeze canonical regression baseline for existing sources`

---

### Fase 1 — Discovery 20minutos (RSS → sitemap → HTML fallback)
**Objetivo**
Identificar la estrategia de ingestión más estable para 20minutos con límites explícitos y sin sobre-scraping.

**Tareas (checklist)**
- [ ] Inventario de entradas de discovery (en este orden):
  1) RSS temáticos (España/política/nacional),
  2) sitemap(s) de noticias,
  3) listado HTML de secciones (fallback final).
- [ ] Validar cada candidato con muestra pequeña (máx. 20 URLs por candidato).
- [ ] Medir señales de calidad por candidato:
  - [ ] disponibilidad de fecha publicable/parsible
  - [ ] cobertura temática relevante
  - [ ] ratio de enlaces válidos vs ruido
- [ ] Seleccionar estrategia primaria + fallback técnico documentado.
- [ ] Definir normalización de fecha a UTC y reglas de deduplicación (`url canónica` + `title`).
- [ ] Documentar guardrails de runtime/retries/caps del adapter.

**Dependencias**
- Fase 0 completada (fecha canónica y entorno validado).

**Riesgos**
- RSS incompleto o con latencia.
- Sitemap masivo con ruido.
- HTML cambiante y frágil.

**Mitigación**
- Priorizar RSS si cobertura aceptable.
- Usar sitemap sólo en rutas acotadas.
- HTML únicamente como fallback y con selectores defensivos.

**Verificación/tests**
- Evidencia de discovery con 1 estrategia ganadora + 1 fallback.
- Reglas explícitas de parada:
  - máx. 3 endpoints por tipo (RSS/sitemap/HTML)
  - máx. 20 items inspeccionados por endpoint
  - timeout por request (p.ej. 10s)
  - máx. 2 reintentos con backoff

**Done criteria**
- Documento de decisión técnica cerrado para 20minutos (fuente primaria y fallback).
- Guardrails cuantificados.

**commit when done:** `docs(discovery): define 20minutos ingestion strategy and guardrails`

---

### Fase 2 — Diseño e implementación del adapter 20minutos (sin romper core)
**Objetivo**
Añadir adapter `20minutos` reutilizando al máximo core compartido y respetando contrato de salida.

**Tareas (checklist)**
- [ ] Crear módulo adapter 20minutos siguiendo convención existente de adapters.
- [ ] Reusar utilidades core de:
  - [ ] HTTP/session/retries
  - [ ] parsing/normalización
  - [ ] serialización JSON/CSV
  - [ ] logging/métricas
- [ ] Implementar pipeline del adapter:
  - [ ] fetch desde estrategia elegida (Fase 1)
  - [ ] extracción de campos estándar
  - [ ] filtrado por fecha UTC
  - [ ] deduplicación
  - [ ] caps de items por run
- [ ] Asegurar compliance de contrato de campos homogéneo con fuentes existentes.
- [ ] Añadir/ajustar tests unitarios del adapter y de normalización de fecha.

**Dependencias**
- Fase 1 (estrategia cerrada).

**Riesgos**
- Divergencias de esquema respecto a adapters actuales.
- Fragilidad ante cambios de HTML.

**Mitigación**
- Validación de esquema común en test compartido.
- Separar parser por estrategia para facilitar fallback.

**Verificación/tests**
- Tests nuevos y existentes en verde.
- Ejecución puntual:
  - `python3 -m src.main --source 20minutos --date YYYY-MM-DD --out data/news_20minutos_YYYY-MM-DD.json`
- Resultado >0 para fecha válida y campos homogéneos.

**Done criteria**
- Adapter operativo aislado, sin tocar lógica core de forma riesgosa.

**commit when done:** `feat(adapter): add 20minutos adapter with utc date filter and guardrails`

---

### Fase 3 — Integración CLI multi-source (compatibilidad total)
**Objetivo**
Exponer `20minutos` en CLI sin degradar fuentes previas ni romper UX/flags.

**Tareas (checklist)**
- [ ] Registrar `20minutos` en catálogo/enrutador de fuentes.
- [ ] Actualizar validaciones de argumento `--source` y help.
- [ ] Asegurar que `--out` y naming de salida siguen patrón estándar.
- [ ] Confirmar que métricas/logs incluyen `source=20minutos` con formato existente.
- [ ] Añadir test de integración CLI para `--source 20minutos`.

**Dependencias**
- Fase 2.

**Riesgos**
- Romper parseo de argumentos o listado de choices.
- Regresión silenciosa en routing de fuentes existentes.

**Mitigación**
- Tests de humo por fuente.
- Mantener cambios mínimos y localizados en capa CLI/router.

**Verificación/tests**
- `python3 -m src.main --help` incluye 20minutos.
- Ejecuciones por fuente (incluyendo previas) sin errores de CLI.

**Done criteria**
- CLI multi-source funcional con nueva fuente y sin breaking changes.

**commit when done:** `feat(cli): wire 20minutos source into multi-source command routing`

---

### Fase 4 — Validación comparativa final + evidencia + rollback
**Objetivo**
Cerrar no-regresión y dejar evidencia auditable de resultado final.

**Tareas (checklist)**
- [ ] Ejecutar batería de verificación del contrato (help + tests + runs por fuente).
- [ ] Re-generar outputs de fuentes previas en fecha canónica y comparar vs baseline Fase 0.
- [ ] Ejecutar run final de 20minutos en fecha canónica.
- [ ] Construir comparativa final:
  - [ ] conteos por fuente (antes/después)
  - [ ] esquema/campos
  - [ ] errores/reintentos/tiempos
- [ ] Documentar en `RESULTS.md`:
  - [ ] evidencia de aceptación
  - [ ] límites conocidos
  - [ ] instrucciones de rollback (hashes de commits atómicos)

**Dependencias**
- Fases 2 y 3.

**Riesgos**
- Variación natural de noticias entre ejecuciones.
- Falsos positivos de regresión por volatilidad temporal.

**Mitigación**
- Comparar estructura + éxito operativo como criterio primario.
- Usar misma fecha canónica y ventana de ejecución acotada.

**Verificación/tests**
- Comandos del contrato ejecutados y registrados.
- Criterios de aceptación marcados como cumplidos con evidencia.

**Done criteria**
- No-regresión razonable demostrada y entrega trazable con rollback claro.

**commit when done:** `test(validation): add comparative regression evidence for existing sources + 20minutos`

---

## 4) Riesgos transversales
- **Técnico:** cambios en estructura de 20minutos (RSS/HTML/sitemap).
  - Mitigación: estrategia jerárquica + fallback + parser defensivo.
- **Operacional:** ejecuciones largas por discovery no acotado.
  - Mitigación: caps explícitos (items/endpoints/retries/timeout).
- **Datos:** duplicados, fechas ambiguas, links no-noticia.
  - Mitigación: dedupe por URL/título + normalización UTC + filtros de relevancia.
- **Seguridad/compliance:** scraping agresivo o fuera de límites.
  - Mitigación: rate-limit básico, sin auth, sin bypass no permitido.

---

## 5) Decision log (human gate)
1. **Cobertura inicial exacta de 20minutos**
   - Opción recomendada: empezar por España/política/nacional con lista cerrada de secciones y ampliar luego por PR aparte.
   - Trade-off: menor cobertura inicial, mayor estabilidad y revisión más limpia.

2. **CSV opcional por defecto**
   - Opción recomendada: mantener comportamiento actual del proyecto (si CSV hoy es opcional, no cambiar default en esta entrega).
   - Trade-off: evita breaking UX; puede requerir segundo comando para generar CSV.

3. **Umbral de no-regresión en conteos**
   - Opción recomendada: sin umbral rígido de conteo; usar criterio combinado (exit code + esquema + ausencia de errores) y reportar diferencias de volumen como observación.
   - Trade-off: menos falso positivo, pero requiere lectura humana de la comparativa.

---

## 6) Execution order summary (handoff implementer)
1. Ejecutar **Fase 0** para fijar baseline canónico y fecha de comparación.
2. Completar **Fase 1** (discovery 20minutos) con límites de exploración y decisión primaria/fallback.
3. Implementar **Fase 2** (adapter 20minutos) reutilizando core y guardrails.
4. Integrar **Fase 3** en CLI multi-source sin romper fuentes previas.
5. Cerrar con **Fase 4** (comparativa final, evidencia en RESULTS, rollback por commits atómicos).

**Primer paso exacto recomendado:** ejecutar preflight + baseline (Fase 0) antes de tocar código del adapter.
