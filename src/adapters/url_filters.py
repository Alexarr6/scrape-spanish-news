from __future__ import annotations

GENERIC_NOISE_URL_FRAGMENTS = (
    "/deportes/",
    "/motor/",
    "/tiempo/",
    "/meteorologia/",
    "/el-tiempo/",
    "/aemet/",
    "/loterias/",
    "/horoscopo/",
    "/shopping/",
    "/compras/",
    "/descuentos/",
    "/branded-content/",
    "/brandstudio/",
    "/publi/",
    "/promociones/",
    "/newsletter/",
    "/video/",
)


def is_probable_noise_url(link: str, *, extra_fragments: tuple[str, ...] = ()) -> bool:
    normalized = link.strip().lower()
    if not normalized:
        return False
    return any(fragment in normalized for fragment in GENERIC_NOISE_URL_FRAGMENTS + extra_fragments)
