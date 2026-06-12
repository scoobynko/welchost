"""First-screen logo: a pixel-art ghost + blocky wordmark.

Matches the jakubsalmik.com aesthetic — monospace, a shell prompt, the terracotta
accent, pixelated block letterforms. No emoji.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from ..themes import ACCENT

# Pixel-art ghost (block characters, two eyes, wavy feet).
GHOST = [
    " ▄███▄ ",
    "███████",
    "█ ▀ ▀ █",
    "█▀█▀█▀█",
]


def _wordmark() -> list[str]:
    from pyfiglet import Figlet

    try:
        art = Figlet(font="double_blocky", width=90).renderText("welchost")
        return [ln for ln in art.splitlines() if ln.strip()]
    except Exception:
        return ["welchost"]


def logo_text() -> Text:
    """Build the splash as a single Rich Text: ghost beside the wordmark."""
    word = _wordmark()
    gw = max(len(g) for g in GHOST)
    # Vertically center the (short) wordmark against the (taller) ghost.
    pad_top = (len(GHOST) - len(word)) // 2
    rows = []
    for i, g in enumerate(GHOST):
        wi = i - pad_top
        right = word[wi] if 0 <= wi < len(word) else ""
        rows.append(f"{g.ljust(gw)}   {right}".rstrip())

    t = Text()
    t.append("~/welchost ", style="dim")
    t.append("❯\n\n", style=f"bold {ACCENT}")
    for row in rows:
        t.append(row + "\n", style=f"bold {ACCENT}")
    t.append("\n")
    t.append("a welcome screen for ghostty\n", style="white")
    t.append("welc + ghost · by scooby", style="dim")
    return t


class Logo(Static):
    """Renders the splash wordmark (uses render() for reliable measuring)."""

    DEFAULT_CSS = """
    Logo { height: auto; padding: 1 2 0 2; }
    """

    def render(self) -> Text:
        return logo_text()
