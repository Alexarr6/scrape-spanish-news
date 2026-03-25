from __future__ import annotations

from src.adapters.discovery_profile import LocalityPenaltyRule, SourceDiscoveryProfile
from src.adapters.profiled_adapter import ProfiledRSSAdapter


class ABCAdapter(ProfiledRSSAdapter):
    source = "abc"
    profile = SourceDiscoveryProfile(
        seed_feeds=(
            "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",
            "https://www.abc.es/rss/feeds/abc_espana.xml",
            "https://www.abc.es/rss/feeds/abc_Politica.xml",
            "https://www.abc.es/rss/feeds/abc_ultimas_noticias.xml",
        ),
        seed_sitemaps=(
            "https://www.abc.es/sitemap.xml",
            "https://www.abc.es/sitemap-news.xml",
        ),
        seed_html_pages=(
            "https://www.abc.es/espana/",
            "https://www.abc.es/espana/politica/",
        ),
        include_path_patterns=("/espana/", "/politica/", "/nacional/"),
        exclude_path_patterns=(
            "/loter",
            "/horoscopo/",
            "/tiempo/",
            "/meteorologia/",
            "/deportes/",
            "/futbol/",
            "/cultura/",
            "/gente/",
            "/viajar/",
            "/familia/",
        ),
        exclude_section_patterns=("opinion", "tribuna", "editorial", "lotería", "loteria"),
        locality_penalty_rules=(
            LocalityPenaltyRule(
                patterns=(
                    "/andalucia/",
                    "/madrid/",
                    "/cataluna/",
                    "/castilla-leon/",
                    "/castilla-la-mancha/",
                    "/galicia/",
                    "/sevilla/",
                    "/jaen/",
                    "/cordoba/",
                ),
                penalty=1,
            ),
        ),
        bucket_rules={
            "politics": ("politica", "gobierno", "congreso", "senado", "tribunal"),
            "society": ("sucesos", "seguridad", "sanidad", "vivienda"),
            "international": ("internacional", "ue", "otan", "gaza", "iran"),
            "economy": ("economia", "energia", "presupuesto", "empleo"),
        },
    )
