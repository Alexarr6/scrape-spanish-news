from __future__ import annotations

from .rss_adapter import GenericRSSAdapter


class ElPaisAdapter(GenericRSSAdapter):
    source = "elpais"
    feeds = [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
    ]
