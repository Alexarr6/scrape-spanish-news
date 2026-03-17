## Resumen
- El fallo de `article_text` está brutalmente concentrado en **El Mundo**: `data/sched_elmundo_2026-03-16.json` tiene **17 artículos / 14 vacíos (82.4%)**; la evidencia histórica del repo es peor: `tests/fixtures/evidence/.../canon2_elmundo_2026-03-13.json` y `reg2_elmundo_2026-03-13.json` tienen **25/25 vacíos**.
- Otras fuentes del mismo día salen sanas o casi sanas: `abc 0/56`, `20minutos 0/10`, `eldiario 0/6`, `lavanguardia 0/9`, `elpais 3/70`.
- `src/adapters/elmundo.py` no tiene lógica propia; hereda de `GenericRSSAdapter`.
- La extracción común actual en `src/adapters/rss_adapter.py` solo intenta `articleBody` desde `application/ld+json` con `json.loads()`. Si el JSON-LD viene roto, se abandona y `article_text` queda vacío.
- Ya hay evidencia previa de que, en El Mundo, muchas páginas contienen `articleBody` pero el bloque JSON-LD se rompe por comillas sin escapar dentro del texto. A la vez, el HTML visible del cuerpo sí existe bajo markup tipo `ue-c-article__body` / `ue-c-article__paragraph`.
- Conclusión de planning: **sí hay que evaluar varias rutas**, pero la mejor primera implementación no es “arreglar JSON roto globalmente” sino una solución **acotada, verificable y con poco radio de explosión**.

## Qué hay hoy en el código y tests
- `src/adapters/rss_adapter.py`
  - `GenericRSSAdapter.normalize()` rellena `article_text` con `_read_article_text(page)`.
  - `_read_article_text()` solo recorre `_extract_json_ld_values(page, "articleBody")`.
  - `_extract_json_ld_values()` parsea cada script JSON-LD con `json.loads()` y descarta cualquier bloque con `JSONDecodeError`.
- `src/adapters/elmundo.py`
  - No añade fallback ni selectores propios.
- `tests/test_rss_adapter_extraction.py`
  - Cubre caso feliz de JSON-LD válido y ausencia de datos.
  - No cubre JSON-LD malformado, ni fallback HTML, ni comportamiento específico de El Mundo.

## Hipótesis priorizadas
1. **Hipótesis principal — fragilidad del parser JSON-LD en El Mundo**
   - El medio publica `articleBody` en JSON-LD, pero una fracción relevante de páginas mete comillas dobles sin escapar dentro del string.
   - `json.loads()` falla, el extractor común descarta el bloque entero y se pierde texto válido.
   - Esto explica por qué el fallo es específico de fuente y no general del pipeline.

2. **Hipótesis secundaria — HTML del cuerpo está disponible y es recuperable con selectores acotados**
   - El Mundo expone el cuerpo en el HTML ya descargado por el scraper, así que no hace falta browser automation ni inventarse bypasses.
   - El riesgo real no es “no hay texto”; el riesgo es extraer demasiado ruido si se hace un fallback HTML chapucero.

3. **Hipótesis menor — puede existir una mejora común útil, pero solo si va muy acotada**
   - Alguna recuperación común de JSON-LD o helper HTML reutilizable podría tener sentido.
   - Pero meter heurísticas globales agresivas por un bug localizado sería una idea bastante mala: más blast radius, más falsos positivos, más mantenimiento.

## Alternativas de implementación evaluadas

### Opción 1 — Fallback HTML específico en `ElMundoAdapter`
**Idea**
- Mantener la ruta actual como primera opción.
- Si `_read_article_text(page)` devuelve vacío en El Mundo, extraer desde el cuerpo HTML usando selectores de esa fuente (`ue-c-article__body`, `ue-c-article__paragraph`, o equivalente realmente observado en fixture real).

**Dónde tocar**
- `src/adapters/elmundo.py`
- Posiblemente factorizar un helper mínimo en `src/adapters/rss_adapter.py` o helper privado local si hace falta limpieza/unión de párrafos.
- Nuevos tests específicos de El Mundo y/o ampliación de `tests/test_rss_adapter_extraction.py`.

**Correctness**
- Alta para el caso objetivo si los selectores se basan en HTML real.
- Respeta la prioridad actual: si JSON-LD válido existe, se sigue usando.

**Blast radius**
- Bajo. Solo afecta a El Mundo.

**Mantenimiento**
- Moderado-bajo. Si El Mundo cambia clases CSS, rompe solo este adapter, no todo el scraper.

**Testabilidad**
- Alta. Se puede fixturear HTML real recortado y comprobar exactamente cuándo entra el fallback.

**Riesgo de falsos positivos / texto ruidoso**
- Medio, pero controlable con selectores estrictos y exclusión de contenedores no editoriales.
- Riesgos concretos: captions, módulos relacionados, promos, duplicados si se mezcla contenedor + párrafos sin cuidado.

**Veredicto**
- **Recomendada como primera implementación.** Es la opción más segura y con mejor relación cobertura/riesgo.

---

### Opción 2 — Estrategia común más segura para recuperar `articleBody` desde JSON-LD
**Idea**
- Mejorar `_extract_json_ld_values()` para tolerar ciertos fallos sin hacer regex satánicas.
- Ejemplos aceptables de alcance:
  - recorrer múltiples blobs y registrar si un script falló;
  - intentar parsear listas/objetos ya válidos más robustamente;
  - añadir una recuperación muy acotada solo para `articleBody` si el script tiene estructura reconocible y delimitable con seguridad.

**Dónde tocar**
- `src/adapters/rss_adapter.py`
- Tests comunes en `tests/test_rss_adapter_extraction.py`

**Correctness**
- Variable. Puede recuperar texto sin depender de CSS, lo cual mola.
- Pero cuando el problema es JSON malformado con comillas internas en texto largo, arreglarlo genéricamente sin tragarte basura es difícil.

**Blast radius**
- Medio-alto. Cambia comportamiento compartido por todas las fuentes.

**Mantenimiento**
- Medio-alto. Las heurísticas para “JSON casi válido” envejecen fatal.

**Testabilidad**
- Media. Se puede testear, sí, pero cuesta demostrar que no rompe otros casos raros.

**Riesgo de falsos positivos / texto ruidoso**
- Medio-alto. Un parser de rescate demasiado listo puede capturar strings truncados, trozos mal delimitados o JSON parcialmente corrupto.

**Veredicto**
- **No recomendada como primer fix.** Solo merece una segunda iteración si, tras arreglar El Mundo de forma local, aparece el mismo patrón en más fuentes y con suficiente evidencia.

---

### Opción 3 — Fallback en parser/helper común pero con alcance fuertemente acotado
**Idea**
- Añadir una capacidad común de extracción HTML, pero no activarla globalmente “porque sí”.
- Ejemplos sensatos:
  - helper compartido de limpieza/unión de párrafos HTML;
  - función común que recibe selectores explícitos por fuente;
  - fallback HTML invocado solo por adapters que lo pidan.

**Dónde tocar**
- `src/adapters/rss_adapter.py` para helper reutilizable pequeño, o nuevo helper privado común.
- `src/adapters/elmundo.py` seguiría decidiendo cuándo usarlo.

**Correctness**
- Alta si el helper es tonto en el buen sentido: extraer nodos dados, limpiar y unir.

**Blast radius**
- Bajo-medio, según diseño. Si el helper es pasivo y no se autoactiva, el riesgo es bajo.

**Mantenimiento**
- Bueno. Evita duplicar utilidades si más adelante otra fuente necesita fallback HTML parecido.

**Testabilidad**
- Alta. Se puede cubrir helper + integración específica.

**Riesgo de falsos positivos / texto ruidoso**
- Bajo-medio si la activación sigue siendo source-specific.

**Veredicto**
- **Buena compañera de la opción 1, no sustituta.** Si al implementar El Mundo aparece duplicación fea de limpieza de párrafos, factorizar helper pequeño sí tiene sentido.

## Comparativa resumida
- **Correctness inmediata para El Mundo:** Opción 1 > Opción 3 > Opción 2
- **Menor blast radius:** Opción 1 ≈ Opción 3 > Opción 2
- **Mantenimiento a corto plazo:** Opción 1 ≈ Opción 3 > Opción 2
- **Testabilidad:** Opción 1 ≈ Opción 3 > Opción 2
- **Menor riesgo de ruido/falsos positivos:** Opción 1 con selectores estrictos / Opción 3 bien diseñada > Opción 2

## Recomendación
**Implementar Opción 1 como cambio principal, con Opción 3 solo si ayuda a no duplicar limpieza trivial.**

En cristiano:
- No tocar el parser común para “reparar” JSON-LD roto de forma global en esta iteración.
- Sí añadir un fallback HTML específico para El Mundo cuando la ruta actual devuelva vacío.
- Si hace falta reutilización, factorizar un helper pequeño y pasivo para limpiar/concatenar párrafos HTML, pero la decisión de usarlo debe quedarse en `ElMundoAdapter`.

## Diseño recomendado para el implementer
Orden de extracción propuesto:
1. Mantener `GenericRSSAdapter` tal como está para todas las fuentes.
2. En `ElMundoAdapter.normalize()`:
   - llamar a la normalización base;
   - si `article.article_text` ya viene no vacío, devolverlo tal cual;
   - si viene vacío, ejecutar fallback HTML específico de El Mundo sobre `raw["html"]`;
   - solo sobrescribir `article_text` si el fallback devuelve texto razonable tras normalización.
3. El fallback HTML debe:
   - priorizar párrafos del cuerpo editorial real;
   - preservar orden;
   - normalizar espacios/entidades;
   - evitar capturar texto de widgets, bloques relacionados, captions o promos;
   - poder devolver `""` si no encuentra un cuerpo fiable.

## Verificación requerida
### Unit tests / fixtures
Añadir cobertura mínima de estos casos:
1. **JSON-LD válido** → El Mundo sigue usando la ruta actual y no cambia el resultado.
2. **JSON-LD inválido + cuerpo HTML real presente** → recupera `article_text` desde HTML.
3. **JSON-LD inválido + no hay contenedor fiable** → devuelve vacío, no rellena basura.
4. **HTML con ruido no editorial cercano** → no captura bloques relacionados/promocionales obvios.
5. **No regresión común** → `tests/test_rss_adapter_extraction.py` sigue verde para comportamiento genérico.

### Evidencia de datos
Repetir y comparar:
```bash
python3 - <<'PY'
import json,glob,os,statistics
for path in sorted(glob.glob('data/sched_*_2026-03-16.json')):
    data=json.load(open(path))
    arts=data if isinstance(data,list) else data.get('articles',[])
    total=len(arts)
    empty=sum(1 for a in arts if not (a.get('article_text') or '').strip())
    lengths=[len((a.get('article_text') or '').strip()) for a in arts if (a.get('article_text') or '').strip()]
    print(os.path.basename(path), total, empty, round(empty/total, 4) if total else None, statistics.median(lengths) if lengths else None)
PY
```

### Muestreo manual
- Revisar 3-5 artículos de El Mundo que antes estaban vacíos.
- Confirmar que el texto recuperado es cuerpo editorial real, no sumario/caption/basura.
- Mirar al menos una noticia por sección distinta si es posible.

## Métricas de éxito
- Principal: bajar El Mundo desde **14/17 vacíos (82.4%)** a **<= 10-15%** en la muestra local del día.
- Secundaria: mantener otras fuentes sin regresión observable.
- Calidad:
  - longitud mediana no absurda;
  - muestreo manual sin ruido editorial serio;
  - cero cambios inesperados en tests comunes.

## Commit boundaries propuestas
### Commit 1 — Reproducción y pruebas
- Añadir fixture(s) HTML recortadas de El Mundo.
- Añadir tests rojos para:
  - JSON-LD válido,
  - JSON-LD inválido con fallback HTML,
  - ausencia de cuerpo fiable.

### Commit 2 — Implementación acotada
- Añadir fallback HTML específico en `src/adapters/elmundo.py`.
- Factorizar helper mínimo solo si evita duplicación trivial.
- Poner todos los tests en verde.

### Commit 3 — Verificación y documentación ligera
- Ejecutar tests focalizados.
- Registrar before/after de ratio de vacíos y notas de muestreo.
- Si el repo lo usa, actualizar doc/changelog/status de implementación.

## Riesgos y guardarraíles
- **Cambio de markup en El Mundo:** usar selectores lo bastante específicos para calidad, pero no una telaraña de CSS imposible de mantener.
- **Ruido editorial:** excluir o evitar bloques de relacionados, promos, captions, newsletters.
- **Duplicado de párrafos:** no mezclar indiscriminadamente texto del contenedor completo y de sus párrafos hijos.
- **Fix demasiado listo en común:** no meter heurísticas globales de “JSON casi válido” en esta iteración.
- **Premium/paywall:** extraer solo lo que ya está en el HTML recibido; nada de bypass raro.

## Handoff inequívoco para implementer
Haz esto y no te líes:
1. **Primero tests.** Crea fixture recortada de El Mundo con:
   - un caso de JSON-LD válido;
   - un caso de JSON-LD malformado por comillas internas sin escapar;
   - cuerpo HTML real bajo markup editorial de El Mundo.
2. Añade test(s) que dejen claro:
   - genérico sigue igual;
   - El Mundo recupera texto por HTML solo cuando JSON-LD falla o viene vacío;
   - sin cuerpo fiable, se mantiene vacío.
3. Implementa el fallback en `src/adapters/elmundo.py`, no como parche global mágico en `rss_adapter.py`.
4. Si necesitas reutilizar limpieza HTML, factoriza helper pequeño y pasivo; no cambies el comportamiento común por defecto.
5. Valida con tests focalizados y revisa muestras recuperadas para asegurar que no metiste porquería.

## Comandos de validación propuestos
```bash
# Tests del extractor común
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_rss_adapter_extraction.py

# Si se añade test específico de El Mundo
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_elmundo_extraction.py

# Suite de adapters si procede
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_*adapter*.py

# Ratios por fuente / longitud mediana
python3 - <<'PY'
import json,glob,os,statistics
for path in sorted(glob.glob('data/sched_*_2026-03-16.json')):
    data=json.load(open(path))
    arts=data if isinstance(data,list) else data.get('articles',[])
    total=len(arts)
    empty=sum(1 for a in arts if not (a.get('article_text') or '').strip())
    lengths=[len((a.get('article_text') or '').strip()) for a in arts if (a.get('article_text') or '').strip()]
    print(os.path.basename(path), 'total=', total, 'empty=', empty, 'ratio=', round(empty/total, 4) if total else None, 'median_len=', statistics.median(lengths) if lengths else None)
PY
```

## Decisiones humanas pendientes
- Aprobación para implementar el fallback HTML **específico de El Mundo**.
- Aprobación para introducir fixtures HTML recortadas basadas en páginas reales.
- Si durante la implementación aparece que varias fuentes sufren el mismo JSON-LD roto, reevaluar una mejora común en una iteración separada; no mezclarlo en este cambio.