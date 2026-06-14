"""Path resolution and environment detection.

Lowest layer of welchost: depends on nothing else in the package. Owns the
module-level ``DEV_MODE`` flag and resolves *where* files live and *whether*
Ghostty is installed.

In DEV mode everything is sandboxed under ``./dev-home/`` relative to the current
working directory, Ghostty is assumed present, and the real ``~/.zshrc`` is never
touched.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Set to True by the CLI ``--dev`` flag (or ``WELCHOST_DEV=1``) before any
# subcommand runs. Never mutate this from inside a command body.
DEV_MODE: bool = False

# Sandbox root for DEV mode, relative to the current working directory.
DEV_HOME = Path("dev-home")

# Shown by the non-interactive `preview` command when Ghostty isn't installed.
# Informational only — preview still renders the banner to stdout.
GHOSTTY_MISSING_NOTICE = (
    "Ghostty isn't installed - the welcome banner only shows in a Ghostty "
    "terminal. Install it from https://ghostty.org, then it'll appear automatically."
)

# Shown by the TUI's blocking gate when Ghostty is missing. There's nothing to
# configure without Ghostty, so the modal offers a single action: quit.
GHOSTTY_REQUIRED_MESSAGE = (
    "Welchost needs Ghostty.\n\n"
    "It builds a welcome screen for the Ghostty terminal, so there's nothing to "
    "set up until Ghostty is installed.\n\n"
    "Install it from https://ghostty.org, then relaunch welchost."
)


def is_dev() -> bool:
    """True if DEV mode is active, honoring the env var as a fallback."""
    return DEV_MODE or os.environ.get("WELCHOST_DEV") == "1"


def get_config_dir() -> Path:
    """Directory that holds welchost.toml, welcome.zsh, welcome_banner.py."""
    if is_dev():
        return DEV_HOME / ".config" / "ghostty"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "ghostty"
    return Path.home() / ".config" / "ghostty"


def get_zshrc() -> Path:
    """Path to the .zshrc that welchost injects its sentinel into."""
    if is_dev():
        return DEV_HOME / ".zshrc"
    return Path.home() / ".zshrc"


def get_config_path() -> Path:
    """Full path to welchost.toml."""
    return get_config_dir() / "welchost.toml"


def get_welcome_zsh_path() -> Path:
    return get_config_dir() / "welcome.zsh"


def get_welcome_banner_path() -> Path:
    return get_config_dir() / "welcome_banner.py"


def get_analytics_path() -> Path:
    """Sidecar file holding the anonymous telemetry id (not part of the config)."""
    return get_config_dir() / "analytics.json"


def ensure_config_dir() -> Path:
    """Create the config dir if needed and return it."""
    d = get_config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def ghostty_installed() -> bool:
    """True if Ghostty is installed. Always True in DEV mode (check skipped)."""
    if is_dev():
        return True
    return (
        Path("/Applications/Ghostty.app").exists()
        or Path("~/Applications/Ghostty.app").expanduser().exists()
        or shutil.which("ghostty") is not None
    )


def term_program() -> str | None:
    """Value of $TERM_PROGRAM, or None if unset."""
    return os.environ.get("TERM_PROGRAM")


def is_ghostty_terminal() -> bool:
    """True if the current terminal reports itself as Ghostty."""
    return term_program() == "ghostty"
