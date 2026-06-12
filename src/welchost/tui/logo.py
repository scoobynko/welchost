"""First-screen logo: an animated pixel-art ghost + a big blocky wordmark.

Matches the jakubsalmik.com aesthetic — monospace, a shell prompt, the terracotta
accent, pixelated block letterforms. No emoji. The ghost gently hovers and blinks
via a timer on the :class:`Logo` widget.
"""

from __future__ import annotations

from functools import lru_cache

from rich.text import Text
from textual.widgets import Static

from .. import __version__
from ..themes import ACCENT

# Pixel-art ghost, built per-frame. The eyes look left/center/right (to read as a
# slow horizontal turn) and the feet wiggle; the whole 4-row ghost drifts gently
# up/down *and* left/right inside a fixed-size "lane" — a slow levitation. The
# lane has constant width and height so the float never reflows the layout or
# shifts the wordmark beside it.
_GHOST_TOP = [" ▄███▄ ", "███████"]
_FEET_A = "█▀█▀█▀█"
_FEET_B = "▀█▀█▀█▀"
_EYE_C = "█ ▀ ▀ █"  # looking ahead
_EYE_L = "█▀ ▀  █"  # turned left
_EYE_R = "█  ▀ ▀█"  # turned right
_EYE_X = "█     █"  # blink

_GHOST_H = 4
_GHOST_W = 7
_V_DRIFT = 2  # rows of vertical travel (1 of headroom each side of center)
_H_DRIFT = 2  # columns of horizontal travel (1 of margin each side of center)
_LANE = _GHOST_H + _V_DRIFT  # fixed row count
_LANE_W = _GHOST_W + _H_DRIFT  # fixed column count

# (eyes, feet, vertical offset, horizontal offset) — a calm idle hover. The ghost
# mostly rests at the centre (1, 1) with just a feet wiggle, and now and then
# nudges a single cell in one direction before settling back. It never strays
# more than one cell from centre and never drifts on both axes at once, so it
# reads as gently levitating in place rather than wandering. One blink per loop.
_FRAMES = [
    (_EYE_C, _FEET_A, 1, 1),  # rest (centre)
    (_EYE_C, _FEET_B, 1, 1),  # rest — feet wiggle only
    (_EYE_C, _FEET_A, 0, 1),  # nudge up
    (_EYE_C, _FEET_B, 1, 1),  # settle
    (_EYE_R, _FEET_A, 1, 2),  # nudge right
    (_EYE_C, _FEET_B, 1, 1),  # settle
    (_EYE_C, _FEET_A, 2, 1),  # nudge down
    (_EYE_C, _FEET_B, 1, 1),  # settle
    (_EYE_L, _FEET_A, 1, 0),  # nudge left
    (_EYE_X, _FEET_B, 1, 1),  # settle + blink
]


def _ghost_frame(frame: int) -> list[str]:
    """One animation frame as exactly ``_LANE`` rows of ``_LANE_W`` columns."""
    eyes, feet, voff, hoff = _FRAMES[frame % len(_FRAMES)]
    ghost = [_GHOST_TOP[0], _GHOST_TOP[1], eyes, feet]
    pad = " " * hoff
    lane = [" " * _LANE_W] * _LANE
    for i, line in enumerate(ghost):
        lane[voff + i] = (pad + line).ljust(_LANE_W)
    return lane


@lru_cache(maxsize=1)
def _wordmark() -> tuple[str, ...]:
    # The wordmark never changes, but logo_text() runs every animation frame
    # (~2×/s for the life of the splash) — cache the pyfiglet render so only the
    # ghost lane is rebuilt per frame.
    from pyfiglet import Figlet

    try:
        art = Figlet(font="double_blocky", width=90).renderText("welchost")
        return tuple(ln for ln in art.splitlines() if ln.strip())
    except Exception:
        return ("welchost",)


def logo_text(frame: int = 0) -> Text:
    """Build the splash as a single Rich Text: ghost beside the big wordmark."""
    word = _wordmark()
    ghost = _ghost_frame(frame)
    gw = max((len(g) for g in ghost), default=0)
    # Vertically center the shorter block against the taller one.
    total = max(len(ghost), len(word))
    g_off = (total - len(ghost)) // 2
    w_off = (total - len(word)) // 2

    t = Text()
    t.append("~/welchost ", style="dim")
    t.append("❯\n\n", style=f"bold {ACCENT}")
    for i in range(total):
        gi, wi = i - g_off, i - w_off
        g = ghost[gi] if 0 <= gi < len(ghost) else ""
        w = word[wi] if 0 <= wi < len(word) else ""
        t.append(g.ljust(gw), style=f"bold {ACCENT}")
        t.append("   ")
        t.append(w + "\n", style=f"bold {ACCENT}")
    t.append(f"\nv{__version__} · by scooby · jakubsalmik.com", style="dim")
    return t


class Logo(Static):
    """Renders the splash; animates the ghost via a timer (uses render() so the
    auto-height is measured reliably)."""

    DEFAULT_CSS = """
    Logo { height: auto; padding: 1 2 0 2; }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._frame = 0

    def on_mount(self) -> None:
        self.set_interval(0.5, self._tick)

    def _tick(self) -> None:
        self._frame += 1
        self.refresh()

    def render(self) -> Text:
        return logo_text(self._frame)
