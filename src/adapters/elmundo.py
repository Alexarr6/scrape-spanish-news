from __future__ import annotations

from .rss_adapter import GenericRSSAdapter


class ElMundoAdapter(GenericRSSAdapter):
    source = "elmundo"
    feeds = [
        "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
        "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    ]
