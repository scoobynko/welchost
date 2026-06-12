"""Render welcome.zsh + welcome_banner.py and manage the .zshrc sentinel.

Uses :mod:`welchost.detect` for all paths and :class:`WelchostConfig` for the
data. The figlet art is rendered with pyfiglet at *generation* time and baked
into welcome_banner.py, so the generated script needs no third-party imports at
runtime.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from pyfiglet import Figlet

from . import __version__, detect
from .config import WelchostConfig

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

# pyfiglet width per size.
SIZE_WIDTH = {"auto": 80, "sm": 60, "md": 80, "lg": 110, "xl": 140}


def resolve_color(value: str) -> tuple[int, int, int]:
    """Resolve a Rich color name or #rrggbb hex to an (r, g, b) tuple."""
    value = (value or "").strip()
    if value.startswith("#"):
        h = value.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        try:
            return tuple(bytes.fromhex(h))  # type: ignore[return-value]
        except ValueError:
            return (204, 204, 204)
    return NAMED_COLORS.get(value.lower(), (204, 204, 204))


def _env() -> Environment:
    return Environment(
        loader=PackageLoader("welchost", "templates"),
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
    )


def build_figlet(config: WelchostConfig) -> str:
    """Render the banner text to ASCII art with pyfiglet."""
    width = SIZE_WIDTH.get(config.banner.size, 80)
    fig = Figlet(font=config.banner.font, width=width)
    return fig.renderText(config.banner.text).rstrip("\n")


# --- template rendering ------------------------------------------------------


def render_welcome_zsh(config: WelchostConfig) -> str:
    template = _env().get_template("welcome.zsh.j2")
    return template.render(
        version=__version__,
        banner_path=str(detect.get_welcome_banner_path()),
    )


def render_welcome_banner(config: WelchostConfig) -> str:
    art = build_figlet(config)
    border_rgb = (
        None
        if config.decoration.border_style == "none"
        else resolve_color(config.decoration.border_color)
    )
    template = _env().get_template("welcome_banner.py.j2")
    return template.render(
        version=__version__,
        art_json=json.dumps(art),
        color_mode=config.banner.color_mode,
        solid_rgb=repr(resolve_color(config.solid.value)),
        grad_start_rgb=repr(resolve_color(config.gradient.start)),
        grad_end_rgb=repr(resolve_color(config.gradient.end)),
        border_style=config.decoration.border_style,
        border_rgb=repr(border_rgb),
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
    """Write welcome.zsh and welcome_banner.py, creating the config dir."""
    detect.ensure_config_dir()
    zsh_path = detect.get_welcome_zsh_path()
    banner_path = detect.get_welcome_banner_path()
    zsh_path.write_text(render_welcome_zsh(config))
    zsh_path.chmod(0o755)
    banner_path.write_text(render_welcome_banner(config))
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
    line = f'[[ "$TERM_PROGRAM" == "ghostty" && $- == *i* ]] && source {src}'
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
