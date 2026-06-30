"""Parity tests: Rich preview vs. generated-script output must be WYSIWYG-identical.

These are characterization/guard tests that lock in existing correct behaviour so
regressions are caught early. If a test fails, first check whether the harness
comparison is unfair before assuming a product bug.

Harness guardrails (all enforced below):
- ``align="left"`` only — center/right depend on terminal width, which differs
  between the Rich Console and the generated script's ``shutil.get_terminal_size``
  fallback, making those comparisons inherently flaky.
- All info flags disabled — info lines include ``datetime.now()`` / ``getuser()``
  / hostname and would flake. Parity here covers art rendering only; info styling
  is Phase 2.
- Fixed font ``"standard"``, short ASCII text.
"""

from __future__ import annotations

import contextlib
import io
import re

import pytest
from rich.console import Console

from welchost.config import GradientColor, Row, SolidColor, WelchostConfig
from welchost.generator import render_welcome_banner
from welchost.render import render_banner

# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _visible_grid(s: str) -> list[str]:
    """ANSI-stripped, rstripped lines with leading/trailing blank lines removed."""
    lines = [_strip_ansi(ln).rstrip() for ln in s.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _color_codes(s: str) -> list[tuple[str, str, str]]:
    """Ordered list of (r, g, b) string tuples from ``38;2;r;g;b`` sequences."""
    return re.findall(r"38;2;(\d+);(\d+);(\d+)", s)


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------


def _capture_rich(cfg: WelchostConfig) -> str:
    """Render the banner via Rich Console and return the captured ANSI string."""
    console = Console(
        width=200,
        force_terminal=True,
        color_system="truecolor",
        legacy_windows=False,
    )
    with console.capture() as cap:
        console.print(render_banner(cfg))
    return cap.get()


def _capture_generated(cfg: WelchostConfig) -> str:
    """Exec the generated welcome_banner.py source and capture stdout of render()."""
    source = render_welcome_banner(cfg)
    ns: dict = {"__name__": "not_main"}
    exec(compile(source, "welcome_banner.py", "exec"), ns)  # noqa: S102
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["render"]()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Config factories (all: align="left", info all off, font="standard")
# ---------------------------------------------------------------------------


def _base_cfg() -> WelchostConfig:
    cfg = WelchostConfig.default()
    cfg.banner.font = "standard"
    cfg.banner.align = "left"
    cfg.info.show_user = False
    cfg.info.show_datetime = False
    cfg.info.show_host = False
    cfg.info.show_os = False
    cfg.info.show_uptime = False
    cfg.info.show_shell = False
    cfg.info.show_python = False
    cfg.info.show_ip = False
    return cfg


def _cfg_solid_two_rows_no_border() -> WelchostConfig:
    """Case 1: two solid rows (red / blue), border=none, no ornament."""
    cfg = _base_cfg()
    cfg.decoration.border_style = "none"
    cfg.ornament.name = "none"
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="red")),
        Row(text="Yo", color_mode="solid", solid=SolidColor(value="blue")),
    ]
    return cfg


def _cfg_gradient_two_rows_no_border() -> WelchostConfig:
    """Case 2: two gradient rows (cyan→magenta horizontal; #ff6b35→#f7c59f diagonal), border=none."""  # noqa: E501
    cfg = _base_cfg()
    cfg.decoration.border_style = "none"
    cfg.ornament.name = "none"
    cfg.banner.rows = [
        Row(
            text="Hi",
            color_mode="gradient",
            gradient=GradientColor(start="cyan", end="magenta", direction="horizontal"),
        ),
        Row(
            text="Yo",
            color_mode="gradient",
            gradient=GradientColor(start="#ff6b35", end="#f7c59f", direction="diagonal"),
        ),
    ]
    return cfg


def _cfg_solid_two_rows_box_border() -> WelchostConfig:
    """Case 3: two solid rows, border=box."""
    cfg = _base_cfg()
    cfg.decoration.border_style = "box"
    cfg.decoration.border_color = "cyan"
    cfg.ornament.name = "none"
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="red")),
        Row(text="Yo", color_mode="solid", solid=SolidColor(value="blue")),
    ]
    return cfg


def _cfg_gradient_one_row_ghosts() -> WelchostConfig:
    """Case 4: one gradient row, ornament=ghosts, border=none."""
    cfg = _base_cfg()
    cfg.decoration.border_style = "none"
    cfg.ornament.name = "ghosts"
    cfg.banner.rows = [
        Row(
            text="Hi",
            color_mode="gradient",
            gradient=GradientColor(start="cyan", end="magenta", direction="horizontal"),
        ),
    ]
    return cfg


def _cfg_mixed_two_rows_rounded() -> WelchostConfig:
    """Case 5: one solid + one gradient row, border=rounded."""
    cfg = _base_cfg()
    cfg.decoration.border_style = "rounded"
    cfg.decoration.border_color = "magenta"
    cfg.ornament.name = "none"
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="red")),
        Row(
            text="Yo",
            color_mode="gradient",
            gradient=GradientColor(start="cyan", end="magenta", direction="horizontal"),
        ),
    ]
    return cfg


_PARITY_CONFIGS = [
    pytest.param(_cfg_solid_two_rows_no_border, id="solid-two-rows-no-border"),
    pytest.param(_cfg_gradient_two_rows_no_border, id="gradient-two-rows-no-border"),
    pytest.param(_cfg_solid_two_rows_box_border, id="solid-two-rows-box"),
    pytest.param(_cfg_gradient_one_row_ghosts, id="gradient-one-row-ghosts"),
    pytest.param(_cfg_mixed_two_rows_rounded, id="mixed-two-rows-rounded"),
]


# ---------------------------------------------------------------------------
# Parity test (one parametrised function → 5 test cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cfg_factory", _PARITY_CONFIGS)
def test_render_vs_generated_parity(cfg_factory):
    """Rich preview and generated script must produce WYSIWYG-identical output.

    Asserts two independent properties per config:
    1. Visible grid — ANSI-stripped, rstripped lines (what the user actually sees).
    2. Color fidelity — ordered list of 24-bit RGB triples from ``38;2;r;g;b``
       ANSI sequences (ensures gradient/solid colours are rendered identically).
    """
    cfg = cfg_factory()
    rich_out = _capture_rich(cfg)
    gen_out = _capture_generated(cfg)

    # 1. Visible (ANSI-stripped) grid must match exactly.
    assert _visible_grid(rich_out) == _visible_grid(gen_out), (
        "Visible grid differs between Rich preview and generated script.\n"
        f"Rich grid ({len(_visible_grid(rich_out))} lines):\n"
        + "\n".join(_visible_grid(rich_out))
        + f"\n\nGenerated grid ({len(_visible_grid(gen_out))} lines):\n"
        + "\n".join(_visible_grid(gen_out))
    )

    # 2. Ordered 24-bit colour triples must match exactly.
    assert _color_codes(rich_out) == _color_codes(gen_out), (
        "Colour sequences differ between Rich preview and generated script.\n"
        f"Rich colours: {_color_codes(rich_out)[:10]}...\n"
        f"Generated colours: {_color_codes(gen_out)[:10]}..."
    )
