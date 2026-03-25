from __future__ import annotations

from src.adapters.discovery_profile import LocalityPenaltyRule, SourceDiscoveryProfile
from src.adapters.profiled_adapter import ProfiledRSSAdapter


class Minutos20Adapter(ProfiledRSSAdapter):
    source = "20minutos"
    profile = SourceDiscoveryProfile(
        seed_feeds=(
            "https://www.20minutos.es/rss/",
            "https://www.20minutos.es/rss/nacional/",
            "https://www.20minutos.es/rss/actualidad/",
        ),
        seed_sitemaps=(
            "https://www.20minutos.es/sitemap-noticias.xml",
            "https://www.20minutos.es/sitemap-news.xml",
            "https://www.20minutos.es/sitemap.xml",
        ),
        seed_html_pages=(
            "https://www.20minutos.es/nacional/",
            "https://www.20minutos.es/minuteca/politica/",
            "https://www.20minutos.es/minuteca/espana/",
        ),
        include_path_patterns=("/nacional/", "/politica/", "/espana/", "/internacional/"),
        exclude_path_patterns=(
            "/deportes/",
            "/loter",
            "/horoscopo/",
            "/tiempo/",
            "/television/",
            "/gente/",
            "/viajes/",
            "/salud/",
        ),
        exclude_section_patterns=("opinión", "opinion", "blogs"),
        locality_penalty_rules=(
            LocalityPenaltyRule(
                patterns=("/madrid/", "/barcelona/", "/sevilla/", "/valencia/", "/malaga/"),
                penalty=1,
            ),
        ),
        bucket_rules={
            "politics": ("politica", "gobierno", "congreso", "senado", "elecciones"),
            "society": ("nacional", "sanidad", "vivienda", "seguridad"),
            "international": ("internacional", "ue", "otan", "gaza", "iran"),
            "economy": ("economia", "empleo", "alquiler", "energia"),
        },
    )
