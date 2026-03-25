from __future__ import annotations

from src.adapters.discovery_profile import LocalityPenaltyRule, SourceDiscoveryProfile
from src.adapters.profiled_adapter import ProfiledRSSAdapter


class ElPaisAdapter(ProfiledRSSAdapter):
    source = "elpais"
    profile = SourceDiscoveryProfile(
        seed_feeds=(
            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
            "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada",
        ),
        seed_sitemaps=(
            "https://elpais.com/sitemaps/news.xml",
            "https://elpais.com/sitemaps/sitemap.xml",
        ),
        seed_html_pages=(
            "https://elpais.com/espana/",
            "https://elpais.com/internacional/",
            "https://elpais.com/economia/",
        ),
        include_path_patterns=(
            "/espana/",
            "/internacional/",
            "/economia/",
            "/america/",
            "/mexico/",
        ),
        exclude_path_patterns=(
            "/opinion/",
            "/deportes/",
            "/futbol/",
            "/television/",
            "/gente/",
            "/eps/",
            "/babelia/",
            "/cinco-dias/",
        ),
        exclude_section_patterns=("opinión", "opinion", "fútbol", "televisión", "gente"),
        locality_penalty_rules=(
            LocalityPenaltyRule(
                patterns=("/comunidad-valenciana/", "/catalunya/", "/andalucia/", "/madrid/"),
                penalty=1,
            ),
        ),
        bucket_rules={
            "politics": ("espana", "gobierno", "congreso", "senado", "tribunal"),
            "society": ("sanidad", "vivienda", "educacion", "justicia"),
            "international": ("internacional", "europa", "gaza", "iran", "ucran"),
            "economy": ("economia", "energia", "inflacion", "presupuesto"),
        },
    )
