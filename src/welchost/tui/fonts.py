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


@lru_cache(maxsize=1)
def font_options() -> list[tuple[str, str]]:
    """(label, value) pairs for the font dropdown: curated first, then the rest.

    Every pyfiglet font is included so nothing is lost vs. the old search; the
    Select's built-in type-to-jump replaces the separate search box. De-duped so
    a curated font never appears twice.
    """
    seen = set(CURATED)
    ordered = [*CURATED, *(f for f in all_fonts() if f not in seen)]
    return [(name, name) for name in ordered]
