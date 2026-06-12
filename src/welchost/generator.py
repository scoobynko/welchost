"""Render welcome.zsh + welcome_banner.py and manage the .zshrc sentinel.

Uses :mod:`welchost.detect` for all paths and :class:`WelchostConfig` for the
data. The figlet art is rendered with pyfiglet at *generation* time and baked
into welcome_banner.py, so the generated script needs no third-party imports at
runtime.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from pyfiglet import Figlet

from . import __version__, detect
from .config import (
    VALID_ALIGN,
    VALID_BORDER_STYLES,
    VALID_COLOR_MODES,
    VALID_GRADIENT_DIRECTIONS,
    WelchostConfig,
)
from .ornaments import get_ornament

# --- sentinel markers --------------------------------------------------------
SENTINEL_START = "# >>> welchost >>>"
SENTINEL_END = "# <<< welchost <<<"

# --- color resolution --------------------------------------------------------
# Minimal Rich/ANSI color-name -> RGB map covering the names used by themes plus
# the common 16. Unknown names fall back to white.
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "red": (197, 15, 31),
    "green": (19, 161, 14),
    "yellow": (193, 156, 0),
    "blue": (0, 55, 218),
    "magenta": (136, 23, 152),
    "cyan": (58, 150, 221),
    "white": (204, 204, 204),
    "bright_black": (118, 118, 118),
    "bright_red": (231, 72, 86),
    "bright_green": (22, 198, 12),
    "bright_yellow": (249, 241, 165),
    "bright_blue": (59, 120, 255),
    "bright_magenta": (180, 0, 158),
    "bright_cyan": (97, 214, 214),
    "bright_white": (242, 242, 242),
    "grey": (128, 128, 128),
    "gray": (128, 128, 128),
}

# Wrap width handed to pyfiglet. Kept large so wide / outline fonts render the
# whole word on one line instead of wrapping each letter onto extra rows; the
# chosen font *is* the size. (pyfiglet only wraps when text exceeds this — it
# does not pad to the width — so a big value costs nothing for small fonts.)
FIGLET_WIDTH = 1000


FALLBACK_RGB = (204, 204, 204)


def resolve_color(value: str) -> tuple[int, int, int]:
    """Resolve a Rich color name or #rgb / #rrggbb hex to an (r, g, b) tuple.

    Always returns a 3-tuple. Anything unparseable — an unknown name, or a hex of
    the wrong length (including the partial values typed live in the color field,
    e.g. ``#ff``, or a malformed value from a hand-edited welchost.toml) — falls
    back to a neutral gray instead of returning a wrong-length tuple that would
    crash the caller's ``r, g, b = resolve_color(...)`` unpack.
    """
    value = (value or "").strip()
    if value.startswith("#"):
        h = value[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            return FALLBACK_RGB
        try:
            r, g, b = bytes.fromhex(h)
        except ValueError:
            return FALLBACK_RGB
        return (r, g, b)
    return NAMED_COLORS.get(value.lower(), FALLBACK_RGB)


def _env() -> Environment:
    return Environment(
        loader=PackageLoader("welchost", "templates"),
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
    )


def font_exists(name: str) -> bool:
    """True if ``name`` is a valid pyfiglet font."""
    from pyfiglet import FigletFont

    try:
        FigletFont(font=name)
        return True
    except Exception:
        return False


@lru_cache(maxsize=64)
def _render_figlet(font: str, text: str) -> str:
    """Cached pyfiglet render keyed by (font, text). The TUI preview re-renders on
    every keystroke — including color/border edits that change neither font nor
    text — so memoizing avoids reconstructing/reparsing the font each time."""
    try:
        fig = Figlet(font=font, width=FIGLET_WIDTH)
    except Exception:
        fig = Figlet(font="standard", width=FIGLET_WIDTH)
    return fig.renderText(text).rstrip("\n")


def build_figlet(config: WelchostConfig) -> str:
    """Render the banner text to ASCII art with pyfiglet at the font's native size.

    Falls back to the ``standard`` font if the configured font is missing, so a
    bad font name can never crash generation or install.
    """
    return _render_figlet(config.banner.font, config.banner.text)


# --- template rendering ------------------------------------------------------


def render_welcome_zsh(config: WelchostConfig) -> str:
    template = _env().get_template("welcome.zsh.j2")
    return template.render(
        version=__version__,
        banner_path=str(detect.get_welcome_banner_path()),
    )


def _enum(value: str, allowed: tuple[str, ...], default: str) -> str:
    """Clamp an enum-valued config string to a known-safe member.

    These strings are interpolated verbatim into the generated welcome_banner.py
    source. welchost.toml is user-editable and shareable, so a value like
    ``align = '"; __import__("os").system("…")'`` must never reach the template —
    clamping to the schema's allowed set closes that code-injection vector and
    also guards against typos.
    """
    return value if value in allowed else default


def render_welcome_banner(config: WelchostConfig) -> str:
    art = build_figlet(config)
    # Clamp every enum baked as a raw string into the generated Python source.
    align = _enum(config.banner.align, VALID_ALIGN, "left")
    color_mode = _enum(config.banner.color_mode, VALID_COLOR_MODES, "solid")
    grad_direction = _enum(config.gradient.direction, VALID_GRADIENT_DIRECTIONS, "horizontal")
    border_style = _enum(config.decoration.border_style, VALID_BORDER_STYLES, "none")

    border_rgb = None if border_style == "none" else resolve_color(config.decoration.border_color)
    orn_left, orn_right = get_ornament(config.ornament.name)
    orn_color = config.gradient.start if color_mode == "gradient" else config.solid.value
    orn_rgb = resolve_color(orn_color) if (orn_left or orn_right) else None
    template = _env().get_template("welcome_banner.py.j2")
    return template.render(
        version=__version__,
        art_json=json.dumps(art),
        align=align,
        color_mode=color_mode,
        grad_direction=grad_direction,
        solid_rgb=repr(resolve_color(config.solid.value)),
        grad_start_rgb=repr(resolve_color(config.gradient.start)),
        grad_end_rgb=repr(resolve_color(config.gradient.end)),
        border_style=border_style,
        border_rgb=repr(border_rgb),
        orn_left=json.dumps(orn_left),
        orn_right=json.dumps(orn_right),
        orn_rgb=repr(orn_rgb),
        info=repr(_info_dict(config)),
    )


def _info_dict(config: WelchostConfig) -> dict[str, bool]:
    i = config.info
    return {
        "show_user": i.show_user,
        "show_host": i.show_host,
        "show_os": i.show_os,
        "show_datetime": i.show_datetime,
        "show_uptime": i.show_uptime,
        "show_shell": i.show_shell,
        "show_python": i.show_python,
        "show_ip": i.show_ip,
    }


# --- file writing ------------------------------------------------------------


def write_generated_files(config: WelchostConfig) -> tuple[Path, Path]:
    """Write welcome.zsh and welcome_banner.py, creating the config dir.

    Both files are rendered to strings *before* anything is written, so a render
    error can never leave a half-installed state on disk.
    """
    zsh_text = render_welcome_zsh(config)
    banner_text = render_welcome_banner(config)
    detect.ensure_config_dir()
    zsh_path = detect.get_welcome_zsh_path()
    banner_path = detect.get_welcome_banner_path()
    banner_path.write_text(banner_text)
    zsh_path.write_text(zsh_text)
    zsh_path.chmod(0o755)
    return zsh_path, banner_path


# --- .zshrc sentinel ---------------------------------------------------------


def _sentinel_block() -> str:
    welcome = detect.get_welcome_zsh_path()
    # Use ~ form for the real-home line; absolute for dev.
    if detect.is_dev():
        src = str(welcome)
    else:
        try:
            rel = welcome.relative_to(Path.home())
            src = f"~/{rel}"
        except ValueError:
            src = str(welcome)
    # Gate: interactive Ghostty shells only, and only if the shim is still there
    # (the `-r` guard means a deleted welcome.zsh can't error on every prompt).
    line = f'[[ "$TERM_PROGRAM" == "ghostty" && $- == *i* && -r {src} ]] && source {src}'
    return f"{SENTINEL_START}\n{line}\n{SENTINEL_END}\n"


def backup_zshrc() -> Path | None:
    """Copy the current .zshrc to a timestamped backup. Returns the path."""
    zshrc = detect.get_zshrc()
    if not zshrc.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = zshrc.with_name(f"{zshrc.name}.welchost.bak.{ts}")
    backup.write_text(zshrc.read_text())
    return backup


def has_sentinel(text: str) -> bool:
    return SENTINEL_START in text and SENTINEL_END in text


def _strip_sentinel(text: str) -> str:
    """Remove an existing sentinel block (inclusive). No-op if absent."""
    if SENTINEL_START not in text:
        return text
    lines = text.splitlines(keepends=True)
    out, skipping = [], False
    for ln in lines:
        if ln.strip() == SENTINEL_START:
            skipping = True
            continue
        if ln.strip() == SENTINEL_END:
            skipping = False
            continue
        if not skipping:
            out.append(ln)
    return "".join(out)


def inject_zshrc() -> Path:
    """Idempotently inject the sentinel block into .zshrc. Backs up first."""
    zshrc = detect.get_zshrc()
    zshrc.parent.mkdir(parents=True, exist_ok=True)
    existing = zshrc.read_text() if zshrc.exists() else ""
    if zshrc.exists():
        backup_zshrc()
    # Remove any prior block so we never double-inject, then append fresh.
    cleaned = _strip_sentinel(existing)
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    new = cleaned + ("\n" if cleaned else "") + _sentinel_block()
    zshrc.write_text(new)
    return zshrc


def remove_zshrc_block() -> bool:
    """Remove the sentinel block from .zshrc. Returns True if something changed."""
    zshrc = detect.get_zshrc()
    if not zshrc.exists():
        return False
    existing = zshrc.read_text()
    if not has_sentinel(existing):
        return False
    backup_zshrc()
    zshrc.write_text(_strip_sentinel(existing))
    return True


# --- install / reset ---------------------------------------------------------


def install(config: WelchostConfig) -> dict[str, Path]:
    """Full install: save files + inject .zshrc. Config is saved by caller."""
    zsh_path, banner_path = write_generated_files(config)
    zshrc = inject_zshrc()
    return {"welcome_zsh": zsh_path, "welcome_banner": banner_path, "zshrc": zshrc}


def reset() -> list[Path]:
    """Remove all welchost files and the .zshrc sentinel. Returns removed paths."""
    removed: list[Path] = []
    if detect.is_dev():
        # DEV reset wipes the whole sandbox.
        import shutil

        if detect.DEV_HOME.exists():
            shutil.rmtree(detect.DEV_HOME)
            removed.append(detect.DEV_HOME)
        return removed
    for p in (
        detect.get_config_path(),
        detect.get_welcome_zsh_path(),
        detect.get_welcome_banner_path(),
    ):
        if p.exists():
            p.unlink()
            removed.append(p)
    if remove_zshrc_block():
        removed.append(detect.get_zshrc())
    return removed
