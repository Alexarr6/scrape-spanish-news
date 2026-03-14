# Discovery 20minutos (RSS → sitemap → HTML fallback)

## Decisión aplicada (gate defaults)
- Alcance inicial: URLs relacionadas con **España / política / nacional**.
- Política CSV: sin cambios (sigue inferencia por extensión en `--out`).
- No-regresión: sin umbral bloqueante rígido; warning + diagnóstico si hay caída relevante.

## Endpoints evaluados (máx. 3 por tipo)

### 1) RSS (primario)
1. `https://www.20minutos.es/rss/`
2. `https://www.20minutos.es/rss/nacional/`
3. `https://www.20minutos.es/rss/actualidad/`

Resultado: accesibles y con volumen suficiente para fecha canónica.

### 2) Sitemap (fallback intermedio)
1. `https://www.20minutos.es/sitemap-noticias.xml`
2. `https://www.20minutos.es/sitemap-news.xml`
3. `https://www.20minutos.es/sitemap.xml`

Resultado: actualmente devuelven 404 en validación real; se conservan como capa opcional y no bloqueante.

### 3) HTML fallback (última capa)
1. `https://www.20minutos.es/nacional/`
2. `https://www.20minutos.es/minuteca/politica/`
3. `https://www.20minutos.es/minuteca/espana/`

Resultado: accesibles y útiles como red de seguridad cuando RSS no alcance cobertura.

## Guardrails runtime
- max endpoints por capa: 3
- timeout HTTP: 15s (cliente común)
- retries: 2 con backoff exponencial base 0.4
- cap discovery por run: configurable (`--max-discovery-urls`, default 300)
- cap extracción: configurable (`--max-articles-to-extract`, default 120)
- stop por tiempo: configurable (`--max-runtime-seconds`, default 180)

## Reglas de calidad
- whitelist temática: `/nacional/`, `/politica/`, `/espana/`, `/elecciones`
- deduplicación: por URL exacta durante discovery
- filtrado final por fecha UTC reutilizando pipeline común (`article.published_at[:10] == --date`)
