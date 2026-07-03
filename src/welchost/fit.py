"""Design-time banner width measurement and auto-fit font selection.

Pure core (no Textual). ``auto_fit_font`` takes its candidate font list as an
argument so this module never imports the font catalog from ``welchost.tui``.
"""

from __future__ import annotations

from .config import WelchostConfig
from .generator import _render_figlet
from .ornaments import get_ornament


def _block_width(font: str, text: str) -> int:
    """Widest line of a single row's figlet block (blank edges stripped)."""
    lines = _render_figlet(font, text).splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(ln) for ln in lines), default=0)


def _ornament_pad(cfg: WelchostConfig) -> int:
    """Extra columns the flanking ornament adds (matches render's 3-space gap)."""
    left, right = get_ornament(cfg.ornament.name)
    pad = 0
    lw = max((len(s) for s in left), default=0)
    rw = max((len(s) for s in right), default=0)
    if lw:
        pad += lw + 3
    if rw:
        pad += rw + 3
    return pad


def art_width(cfg: WelchostConfig, font: str | None = None) -> int:
    """Widest rendered line across all banner rows, including ornament flanking."""
    f = font or cfg.banner.font
    widest = max((_block_width(f, row.text) for row in cfg.banner.rows), default=0)
    return widest + _ornament_pad(cfg)


def fits(cfg: WelchostConfig) -> bool:
    """True if the banner is within its fit target (or the target is disabled)."""
    return cfg.banner.fit_width <= 0 or art_width(cfg) <= cfg.banner.fit_width


def auto_fit_font(cfg: WelchostConfig, candidates: list[str]) -> str:
    """Pick the largest candidate font that fits ``cfg.banner.fit_width``.

    If none fit, return the least-overflowing candidate. With the target
    disabled (``fit_width <= 0``) return the widest candidate. Falls back to the
    current font when ``candidates`` is empty.
    """
    if not candidates:
        return cfg.banner.font
    measured = [(f, art_width(cfg, font=f)) for f in candidates]
    target = cfg.banner.fit_width
    if target > 0:
        fitting = [(f, w) for f, w in measured if w <= target]
        if fitting:
            return max(fitting, key=lambda fw: fw[1])[0]
        return min(measured, key=lambda fw: fw[1])[0]
    return max(measured, key=lambda fw: fw[1])[0]
