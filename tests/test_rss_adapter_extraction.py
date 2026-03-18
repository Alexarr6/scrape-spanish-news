from __future__ import annotations

from src.adapters.rss_adapter import GenericRSSAdapter


class _AdapterUnderTest(GenericRSSAdapter):
    source = "testsource"


def test_normalize_populates_article_text_and_tags_from_page_metadata():
    page = """
    <html>
      <head>
        <meta property="og:title" content="  Titular  ">
        <meta name="description" content="  Resumen corto  ">
        <meta property="article:published_time" content="2026-03-15T10:00:00+01:00">
        <meta property="article:section" content=" Política ">
        <meta property="article:tag" content="España">
        <meta property="article:tag" content="Elecciones">
        <script type="application/ld+json">
          {
            "@context":"https://schema.org",
            "@type":"NewsArticle",
            "articleBody":" Primer párrafo.\\n\\nSegundo párrafo. "
          }
        </script>
      </head>
    </html>
    """

    article = _AdapterUnderTest().normalize({"url": "https://example.com/a", "html": page})

    assert article.title == "Titular"
    assert article.summary == "Resumen corto"
    assert article.section == "Política"
    assert article.article_text == "Primer párrafo. Segundo párrafo."
    assert article.tags == "España, Elecciones"
    assert article.published_at == "2026-03-15T09:00:00+00:00"


def test_normalize_falls_back_to_keywords_and_leaves_missing_tags_empty():
    keywords_page = """
    <html>
      <head>
        <meta property="og:title" content="Titular">
        <meta property="article:published_time" content="2026-03-15T10:00:00+01:00">
        <meta name="keywords" content="vox, castilla y león, política">
        <script type="application/ld+json">{"articleBody":"Texto largo"}</script>
      </head>
    </html>
    """
    empty_page = """
    <html>
      <head>
        <meta property="og:title" content="Titular">
        <meta property="article:published_time" content="2026-03-15T10:00:00+01:00">
      </head>
    </html>
    """

    with_keywords = _AdapterUnderTest().normalize(
        {"url": "https://example.com/keywords", "html": keywords_page}
    )
    without_tags = _AdapterUnderTest().normalize(
        {"url": "https://example.com/empty", "html": empty_page}
    )

    assert with_keywords.article_text == "Texto largo"
    assert with_keywords.tags == "vox, castilla y león, política"
    assert without_tags.article_text == ""
    assert without_tags.tags == ""
