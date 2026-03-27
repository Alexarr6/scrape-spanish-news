from __future__ import annotations

from datetime import UTC, date, datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from src.persistence.orm import ArticleORM

MATCHING_TIMEZONE = "Europe/Madrid"

NATIONAL_TERMS = (
    "gobierno",
    "congreso",
    "senado",
    "tribunal",
    "supremo",
    "constitucional",
    "fiscal",
    "minister",
    "moncloa",
    "sanchez",
    "sánchez",
    "pp",
    "psoe",
    "vox",
    "sumar",
    "podemos",
    "junts",
    "erc",
    "pnv",
    "bildu",
    "amnist",
    "presupuest",
    "ley",
    "decreto",
    "renfe",
    "aemet",
    "ue",
    "otan",
    "onu",
)

GLOBAL_EXCLUDE_TERMS = (
    "opinion",
    "opinión",
    "editorial",
    "tribuna",
    "deportes",
    "fútbol",
    "futbol",
    "toros",
    "loter",
    "horoscopo",
    "horóscopo",
    "televisión",
    "television",
    "gente",
    "magazine",
    "eps",
    "babelia",
    "viajes",
    "viajar",
)

SOFT_LIFESTYLE_TERMS = (
    "cultura",
    "familia",
    "beber",
    "belleza",
    "cine",
    "televisión",
    "television",
    "gente",
)

GLOBAL_EXCLUDE_SECTION_TERMS = (
    "opinion",
    "opinión",
    "editorial",
    "tribuna",
    "deportes",
    "fútbol",
    "futbol",
    "toros",
    "televisión",
    "television",
    "gente",
    "magazine",
    "eps",
    "babelia",
    "viajes",
    "viajar",
    "recreo",
    "moda",
    "shopping",
    "compras",
)

GLOBAL_EXCLUDE_PATH_TERMS = (
    "/topics/",
    "/topic/",
    "/temas/",
    "/tema/",
    "/autor/",
    "/autores/",
    "/firmas/",
)

LOCALITY_TERMS = (
    "/andalucia/",
    "/madrid/",
    "/cataluna/",
    "/catalunya/",
    "/castilla",
    "/galicia/",
    "/illes-balears/",
    "/barcelona/",
    "/sevilla/",
    "/malaga/",
    "/valencia/",
    "/jaen/",
    "/cordoba/",
)

BUCKET_PATTERNS = {
    "politics": (
        "politica",
        "política",
        "gobierno",
        "congreso",
        "senado",
        "tribunal",
        "fiscal",
        "amnist",
        "presupuest",
        "ley",
        "decreto",
        "eleccion",
    ),
    "society": (
        "espana",
        "españa",
        "nacional",
        "sociedad",
        "sanidad",
        "salud",
        "vivienda",
        "educacion",
        "educación",
        "seguridad",
        "justicia",
        "sucesos",
        "migr",
    ),
    "international": (
        "internacional",
        "europa",
        "ue",
        "otan",
        "onu",
        "gaza",
        "israel",
        "iran",
        "irán",
        "ucrania",
        "rusia",
        "francia",
        "alemania",
    ),
    "economy": (
        "economia",
        "economía",
        "energia",
        "energía",
        "inflacion",
        "inflación",
        "empleo",
        "alquiler",
        "impuestos",
        "bce",
        "banco central",
    ),
}

SOURCE_EXCLUDE_TERMS = {
    "abc": ("futbol sala", "mundial de atletismo", "semana santa", "parroquia"),
    "elpais": ("cinco dias", "televisión", "gente", "eps"),
    "elmundo": ("toros", "loc"),
    "20minutos": ("sueldazo", "once", "comprobar", "tiempo hará", "aemet avanza"),
    "eldiario": ("opinion", "opinión", "blogs", "vertele", "consumoclaro"),
    "lavanguardia": ("tribuna", "brújula para un mundo extraño"),
}

SOURCE_EXCLUDE_SECTION_TERMS = {
    "abc": ("recreo", "viajar"),
    "20minutos": ("gonzoo", "capaces", "moda", "aplicaciones", "juegos"),
    "eldiario": ("spin", "the guardian", "la gomera ahora", "vertele", "consumoclaro"),
    "elpais": ("cultura",),
    "lavanguardia": ("opinión", "opinion"),
}


def text_blob(row: ArticleORM) -> str:
    return " ".join(
        [
            (row.section or "").casefold(),
            (row.title or "").casefold(),
            (row.summary or "").casefold(),
            (row.tags or "").casefold(),
            (urlparse(row.url).path or "").casefold(),
        ]
    )


def detect_bucket(text: str) -> str:
    best_bucket = ""
    best_score = 0
    for bucket, patterns in BUCKET_PATTERNS.items():
        score = sum(1 for pattern in patterns if pattern in text)
        if score > best_score:
            best_bucket = bucket
            best_score = score
    return best_bucket


def local_published_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(MATCHING_TIMEZONE)).date()
