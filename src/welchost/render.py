"""Shared Rich rendering of a banner from a WelchostConfig.

Textual-free (Rich only) so both the CLI (`preview`) and the TUI live preview
produce the same WYSIWYG output. The generated welcome_banner.py mirrors this
with pure-Python ANSI.
"""

from __future__ import annotations

import getpass
import os
import platform
import socket
from datetime import datetime

from rich.align import Align
from rich.box import ASCII, DOUBLE, HEAVY, ROUNDED, SQUARE
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from .config import WelchostConfig
from .generator import build_figlet, resolve_color
from .ornaments import get_ornament

_BOX_MAP = {
    "panel": HEAVY,
    "box": SQUARE,
    "double": DOUBLE,
    "rounded": ROUNDED,
    "ascii": ASCII,
}


def _blend(s: tuple[int, int, int], e: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return (
        round(s[0] + (e[0] - s[0]) * f),
        round(s[1] + (e[1] - s[1]) * f),
        round(s[2] + (e[2] - s[2]) * f),
    )


def _gradient_factor(col: int, row: int, dx: int, dy: int, direction: str) -> float:
    """Position 0→1 of a character within the block for the given direction."""
    if direction == "vertical":
        return row / dy
    if direction == "diagonal":
        return (col / dx + row / dy) / 2
    return col / dx  # horizontal (default)


def _strip_blank_edges(lines: list[str]) -> list[str]:
    """Drop leading/trailing all-blank lines (mirrors the generated script) so the
    gradient spans exactly the visible rows — otherwise vertical/diagonal blends
    waste range on empty rows and look uneven."""
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def _art_rows(cfg: WelchostConfig, lines: list[str]) -> list[Text]:
    """One styled Text per art line (gradient or solid)."""
    rows: list[Text] = []
    if cfg.banner.color_mode == "gradient":
        s = resolve_color(cfg.gradient.start)
        e = resolve_color(cfg.gradient.end)
        direction = cfg.gradient.direction
        dx = max(max((len(ln) for ln in lines), default=1) - 1, 1)
        dy = max(len(lines) - 1, 1)
        for row, line in enumerate(lines):
            tx = Text()
            for col, ch in enumerate(line):
                f = _gradient_factor(col, row, dx, dy, direction)
                r, g, b = _blend(s, e, f)
                tx.append(ch, style=f"bold rgb({r},{g},{b})")
            rows.append(tx)
    else:
        r, g, b = resolve_color(cfg.solid.value)
        rows = [Text(line, style=f"bold rgb({r},{g},{b})") for line in lines]
    return rows


def _flank(rows: list[Text], cfg: WelchostConfig) -> list[Text]:
    """Place the configured ornament left and right of the art rows, centered."""
    left, right = get_ornament(cfg.ornament.name)
    if not left and not right:
        return rows

    color = cfg.gradient.start if cfg.banner.color_mode == "gradient" else cfg.solid.value
    r, g, b = resolve_color(color)
    style = f"rgb({r},{g},{b})"
    lw = max((len(s) for s in left), default=0)
    rw = max((len(s) for s in right), default=0)
    art_w = max((row.cell_len for row in rows), default=0)
    total = max(len(rows), len(left), len(right))
    a_off = (total - len(rows)) // 2
    l_off = (total - len(left)) // 2
    r_off = (total - len(right)) // 2
    gap = "   "

    out: list[Text] = []
    for i in range(total):
        line = Text()
        if lw:
            ls = left[i - l_off] if 0 <= i - l_off < len(left) else ""
            line.append(ls.ljust(lw), style=style)
            line.append(gap)
        ai = i - a_off
        if 0 <= ai < len(rows):
            line.append_text(rows[ai])
            line.append(" " * (art_w - rows[ai].cell_len))
        else:
            line.append(" " * art_w)
        if rw:
            rs = right[i - r_off] if 0 <= i - r_off < len(right) else ""
            line.append(gap)
            line.append(rs.ljust(rw), style=style)
        out.append(line)
    return out


def render_art(cfg: WelchostConfig) -> Text:
    """The colored figlet block (no border, no info), optionally flanked by an
    ornament.

    Gradient runs across the whole block per ``gradient.direction`` — horizontal
    (left→right), vertical (top→bottom), or diagonal — so the factor is computed
    from each character's position within the block, not just within its line.
    """
    art = build_figlet(cfg)
    lines = _strip_blank_edges(art.splitlines())
    rows = _flank(_art_rows(cfg, lines), cfg)

    block = Text()
    for i, row in enumerate(rows):
        block.append_text(row)
        if i != len(rows) - 1:
            block.append("\n")
    return block


def info_text(cfg: WelchostConfig) -> Text | None:
    rows: list[tuple[str, str]] = []
    i = cfg.info
    if i.show_user:
        rows.append(("user", getpass.getuser()))
    if i.show_host:
        rows.append(("host", socket.gethostname()))
    if i.show_os:
        mac = platform.mac_ver()[0]
        rows.append(("os", f"macOS {mac}" if mac else platform.system()))
    if i.show_datetime:
        rows.append(("date", datetime.now().strftime("%a %d %b %Y · %H:%M")))
    if i.show_uptime:
        rows.append(("uptime", "…"))
    if i.show_shell:
        rows.append(("shell", os.environ.get("SHELL", "?")))
    if i.show_python:
        rows.append(("python", platform.python_version()))
    if i.show_ip:
        rows.append(("ip", "…"))
    if not rows:
        return None
    t = Text()
    for idx, (k, v) in enumerate(rows):
        t.append(f"{k}: ", style="dim")
        t.append(str(v))
        if idx != len(rows) - 1:
            t.append("\n")
    return t


def render_banner(cfg: WelchostConfig) -> RenderableType:
    """Full banner: colored art + info, wrapped in the chosen border.

    The whole block/box is then aligned within the available width per
    ``banner.align`` (left | center | right), so the preview matches how the
    generated script positions the banner in the terminal.
    """
    block = render_art(cfg)
    info = info_text(cfg)
    if info is not None:
        block.append("\n\n")
        block.append_text(info)

    style = cfg.decoration.border_style
    if style == "none":
        renderable: RenderableType = block
    else:
        br, bg, bb = resolve_color(cfg.decoration.border_color)
        renderable = Panel(
            Align.left(block),
            box=_BOX_MAP.get(style, SQUARE),
            border_style=f"rgb({br},{bg},{bb})",
            expand=False,
            padding=(0, 1),
        )

    align = cfg.banner.align if cfg.banner.align in ("left", "center", "right") else "left"
    return Align(renderable, align=align)  # type: ignore[arg-type]
