from __future__ import annotations

from src.adapters.discovery_profile import LocalityPenaltyRule, SourceDiscoveryProfile
from src.adapters.profiled_adapter import ProfiledRSSAdapter


class LaVanguardiaAdapter(ProfiledRSSAdapter):
    source = "lavanguardia"
    profile = SourceDiscoveryProfile(
        seed_feeds=(
            "https://www.lavanguardia.com/rss/home.xml",
            "https://www.lavanguardia.com/rss/politica.xml",
            "https://www.lavanguardia.com/rss/nacional.xml",
        ),
        seed_sitemaps=(
            "https://www.lavanguardia.com/sitemap.xml",
            "https://www.lavanguardia.com/sitemap-noticias.xml",
        ),
        seed_html_pages=(
            "https://www.lavanguardia.com/politica",
            "https://www.lavanguardia.com/politica/nacional",
            "https://www.lavanguardia.com/nacional",
            "https://www.lavanguardia.com/internacional",
        ),
        include_path_patterns=("/politica/", "/nacional/", "/espana/", "/internacional/"),
        exclude_path_patterns=(
            "/deportes/",
            "/cultura/",
            "/gente/",
            "/magazine/",
            "/vida/",
            "/opinion/",
        ),
        exclude_section_patterns=("opinión", "opinion", "tribuna"),
        locality_penalty_rules=(
            LocalityPenaltyRule(
                patterns=("/barcelona/", "/catalunya/", "/local/", "/sucesos/"),
                penalty=1,
            ),
        ),
        bucket_rules={
            "politics": ("politica", "gobierno", "congreso", "senado", "tribunal"),
            "society": ("nacional", "sanidad", "vivienda", "seguridad"),
            "international": ("internacional", "ue", "gaza", "iran", "otan"),
            "economy": ("economia", "energia", "empleo", "impuestos"),
        },
    )
