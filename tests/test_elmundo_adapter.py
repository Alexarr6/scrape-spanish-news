from src.adapters.elmundo import ElMundoAdapter

VALID_JSON_LD_PAGE = """
<html>
  <head>
    <meta property="og:title" content="Titular El Mundo">
    <meta property="article:published_time" content="2026-03-16T10:00:00+01:00">
    <script type="application/ld+json">
      {"@type":"NewsArticle","articleBody":" Texto desde JSON-LD válido. "}
    </script>
  </head>
  <body>
    <div class="ue-c-article__body" data-section="articleBody">
      <p class="ue-c-article__paragraph">Texto fallback que no debería usarse.</p>
    </div>
  </body>
</html>
"""


MALFORMED_JSON_LD_WITH_HTML_FALLBACK_PAGE = """
<html>
  <head>
    <meta property="og:title" content="Robles exige a Israel que cese los ataques">
    <meta property="article:published_time" content="2026-03-16T10:32:00+01:00">
    <script type="application/ld+json">
      {
        "@type":"NewsArticle",
        "articleBody":"Primer párrafo con una cita rota: "
          "hay intercambio de cohetes a diario" y por eso el JSON-LD revienta."
      }
    </script>
  </head>
  <body>
    <div class="ue-c-article__standfirst">
      <p class="ue-c-article__paragraph">Entradilla que no forma parte del cuerpo.</p>
    </div>
    <div class="ue-c-article__body" data-section="articleBody">
      <p class="ue-c-article__paragraph">
        La ministra de Defensa, <strong>Margarita Robles</strong>, ha mantenido este lunes
        una videoconferencia con el contingente español.
      </p>
      <p class="ue-c-article__paragraph">
        Robles trasladó a la ONU la exigencia de que <a href="#">Israel</a> cese los
        ataques y garantice la protección de la misión.
      </p>
    </div>
    <aside class="ue-c-related-news">
      <p class="ue-c-article__paragraph">Relacionada: otra noticia que no debe colarse.</p>
    </aside>
  </body>
</html>
"""


MALFORMED_JSON_LD_WITHOUT_RELIABLE_BODY_PAGE = """
<html>
  <head>
    <meta property="og:title" content="Titular vacío">
    <meta property="article:published_time" content="2026-03-16T10:00:00+01:00">
    <script type="application/ld+json">
      {"@type":"NewsArticle","articleBody":"Texto con comillas rotas: "esto" rompe todo"}
    </script>
  </head>
  <body>
    <div class="ue-c-article__standfirst">
      <p class="ue-c-article__paragraph">Solo hay entradilla.</p>
    </div>
    <aside class="ue-c-related-news">
      <p class="ue-c-article__paragraph">Relacionada: ruido editorial.</p>
    </aside>
  </body>
</html>
"""


def test_elmundo_prefers_generic_json_ld_extraction_when_available():
    article = ElMundoAdapter().normalize(
        {"url": "https://example.com/ok", "html": VALID_JSON_LD_PAGE}
    )

    assert article.article_text == "Texto desde JSON-LD válido."


def test_elmundo_falls_back_to_article_body_html_when_json_ld_is_malformed():
    article = ElMundoAdapter().normalize(
        {
            "url": "https://example.com/fallback",
            "html": MALFORMED_JSON_LD_WITH_HTML_FALLBACK_PAGE,
        }
    )

    assert article.article_text == (
        "La ministra de Defensa, Margarita Robles, ha mantenido este lunes una "
        "videoconferencia con el contingente español. Robles trasladó a la ONU la "
        "exigencia de que Israel cese los ataques y garantice la protección de la misión."
    )
    assert "Entradilla" not in article.article_text
    assert "Relacionada" not in article.article_text


def test_elmundo_keeps_article_text_empty_without_a_reliable_body_container():
    article = ElMundoAdapter().normalize(
        {"url": "https://example.com/empty", "html": MALFORMED_JSON_LD_WITHOUT_RELIABLE_BODY_PAGE}
    )

    assert article.article_text == ""
