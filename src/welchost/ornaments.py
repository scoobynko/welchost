"""Predefined flanking ornaments — small ASCII blocks placed to the left and
right of the banner art (like the parentheses-ghosts a colleague used).

Plain data, no I/O, no dependencies. Shared by ``render.py`` (preview) and the
generated ``welcome_banner.py`` so both flank identically. Each entry is
``(left_lines, right_lines)``; the block is centered vertically against the art.
``none`` disables ornaments.
"""

from __future__ import annotations

ORNAMENTS: dict[str, tuple[list[str], list[str]]] = {
    "none": ([], []),
    # The colleague's look: little parenthesis "ghosts" on each side.
    "ghosts": (
        [" )( ", "( )(", " )( "],
        [" )( ", "( )(", " )( "],
    ),
    "stars": (
        [" ⋆", "✦ ", " ⋆"],
        ["⋆ ", " ✦", "⋆ "],
    ),
    "bars": (
        ["█", "█", "█", "█", "█"],
        ["█", "█", "█", "█", "█"],
    ),
    "dots": (
        ["·", "•", "·"],
        ["·", "•", "·"],
    ),
}

VALID_ORNAMENTS = tuple(ORNAMENTS.keys())


def get_ornament(name: str) -> tuple[list[str], list[str]]:
    """Left/right line lists for ``name``; empty pair if unknown or ``none``."""
    return ORNAMENTS.get(name, ([], []))
