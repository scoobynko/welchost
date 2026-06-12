"""Font lists for the wizard picker."""

from __future__ import annotations

from functools import lru_cache

# Curated shortlist surfaced first in the picker. Filled / block fonts lead
# (Claude / Codex CLI vibe), then a few clean classics. All verified valid.
CURATED = [
    "ansi_shadow",
    "ansi_regular",
    "pagga",
    "block",
    "banner3",
    "colossal",
    "slant",
    "doom",
    "big",
    "standard",
    "isometric1",
    "3d_diagonal",
    "epic",
    "univers",
    "shadow",
    "larry3d",
    "straight",
    "thin",
    "bulbhead",
    "nancyj",
]


@lru_cache(maxsize=1)
def all_fonts() -> list[str]:
    """All pyfiglet fonts, sorted."""
    from pyfiglet import FigletFont

    return sorted(FigletFont.getFonts())


def search_fonts(query: str, limit: int = 60) -> list[str]:
    """Curated first when query is empty, else a filtered match over all fonts."""
    query = (query or "").strip().lower()
    if not query:
        return CURATED
    matches = [f for f in all_fonts() if query in f.lower()]
    return matches[:limit]
