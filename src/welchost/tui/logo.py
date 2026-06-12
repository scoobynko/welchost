"""First-screen logo: a compact terminal-style wordmark.

Matches the jakubsalmik.com aesthetic — monospace, a shell prompt, the terracotta
accent, and a ghost.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from ..themes import ACCENT

GHOST = "👻"


class Logo(Static):
    """Renders the splash wordmark (uses render() for reliable measuring)."""

    DEFAULT_CSS = """
    Logo { height: auto; padding: 1 2 0 2; }
    """

    def render(self) -> Text:
        return logo_text()


def logo_text() -> Text:
    """Build the splash as a single Rich Text (compact pagga wordmark)."""
    from pyfiglet import Figlet

    try:
        art = Figlet(font="pagga", width=80).renderText("welchost").rstrip("\n")
    except Exception:
        art = "welchost"
    lines = [ln for ln in art.splitlines() if ln.strip()]

    t = Text()
    t.append("~/welchost ", style="dim")
    t.append("❯\n\n", style=f"bold {ACCENT}")
    for i, line in enumerate(lines):
        prefix = f"{GHOST}  " if i == 0 else "    "
        t.append(prefix)
        t.append(line + "\n", style=f"bold {ACCENT}")
    t.append("\n")
    t.append("a welcome screen for ghostty\n", style="white")
    t.append("welc + ghost · by scooby", style="dim")
    return t
