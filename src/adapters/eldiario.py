from __future__ import annotations

import re

from src.adapters.discovery_profile import LocalityPenaltyRule, SourceDiscoveryProfile
from src.adapters.profiled_adapter import ProfiledRSSAdapter


class ElDiarioAdapter(ProfiledRSSAdapter):
    source = "eldiario"
    profile = SourceDiscoveryProfile(
        seed_feeds=(
            "https://www.eldiario.es/rss/",
            "https://www.eldiario.es/rss/politica/",
            "https://www.eldiario.es/rss/sociedad/",
        ),
        seed_sitemaps=(
            "https://www.eldiario.es/sitemap_index.xml",
            "https://www.eldiario.es/sitemap_google_news.xml",
            "https://www.eldiario.es/sitemap.xml",
        ),
        seed_html_pages=(
            "https://www.eldiario.es/politica/",
            "https://www.eldiario.es/sociedad/",
            "https://www.eldiario.es/madrid/politica/",
            "https://www.eldiario.es/",
        ),
        include_path_patterns=(
            "/politica/",
            "/sociedad/",
            "/nacional/",
            "/espana/",
            "/internacional/",
        ),
        exclude_path_patterns=(
            "/deportes/",
            "/opinion/",
            "/blogs/",
            "/cultura/",
            "/consumoclaro/",
            "/vertele/",
        ),
        exclude_section_patterns=("opinión", "opinion", "tribuna"),
        locality_penalty_rules=(
            LocalityPenaltyRule(
                patterns=(
                    "/illes-balears/",
                    "/canariasahora/",
                    "/euskadi/",
                    "/galicia/",
                    "/andalucia/",
                    "/catalunya/",
                    "/madrid/",
                ),
                penalty=1,
            ),
        ),
        bucket_rules={
            "politics": ("politica", "gobierno", "congreso", "juez", "tribunal"),
            "society": ("sociedad", "sanidad", "vivienda", "educacion"),
            "international": ("internacional", "ue", "gaza", "iran", "otan"),
            "economy": ("economia", "empleo", "impuestos", "presupuesto"),
        },
        minimum_usable_candidates=18,
    )

    def _collect_sitemaps_from_robots(self) -> list[str]:
        try:
            robots = self.http.get_text("https://www.eldiario.es/robots.txt")
        except Exception:
            return []
        found = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
        out: list[str] = []
        seen: set[str] = set()
        for sitemap in found:
            sitemap = sitemap.strip()
            if sitemap and sitemap not in seen:
                seen.add(sitemap)
                out.append(sitemap)
        return out

    def _sitemap_seeds(self) -> list[str]:
        return list(self.profile.seed_sitemaps) + self._collect_sitemaps_from_robots()[:3]
