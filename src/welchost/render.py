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

_BOX_MAP = {
    "panel": HEAVY,
    "box": SQUARE,
    "double": DOUBLE,
    "rounded": ROUNDED,
    "ascii": ASCII,
}


def _gradient_line(line: str, start: str, end: str) -> Text:
    s = resolve_color(start)
    e = resolve_color(end)
    n = max(len(line) - 1, 1)
    t = Text()
    for i, ch in enumerate(line):
        f = i / n
        r = round(s[0] + (e[0] - s[0]) * f)
        g = round(s[1] + (e[1] - s[1]) * f)
        b = round(s[2] + (e[2] - s[2]) * f)
        t.append(ch, style=f"bold rgb({r},{g},{b})")
    return t


def render_art(cfg: WelchostConfig) -> Text:
    """The colored figlet block (no border, no info)."""
    art = build_figlet(cfg)
    lines = art.splitlines()
    block = Text()
    for idx, line in enumerate(lines):
        if cfg.banner.color_mode == "gradient":
            block.append_text(_gradient_line(line, cfg.gradient.start, cfg.gradient.end))
        else:
            r, g, b = resolve_color(cfg.solid.value)
            block.append(line, style=f"bold rgb({r},{g},{b})")
        if idx != len(lines) - 1:
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
    """Full banner: colored art + info, wrapped in the chosen border."""
    block = render_art(cfg)
    info = info_text(cfg)
    if info is not None:
        block.append("\n\n")
        block.append_text(info)

    style = cfg.decoration.border_style
    if style == "none":
        return block
    br, bg, bb = resolve_color(cfg.decoration.border_color)
    return Panel(
        Align.left(block),
        box=_BOX_MAP.get(style, SQUARE),
        border_style=f"rgb({br},{bg},{bb})",
        expand=False,
        padding=(0, 1),
    )
