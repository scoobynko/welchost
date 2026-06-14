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


def _ghostty_app_present() -> bool:
    """True if a Ghostty install is found on disk (app bundle or known binary)."""
    candidates = (
        Path("/Applications/Ghostty.app"),
        Path("~/Applications/Ghostty.app").expanduser(),
        Path("/opt/homebrew/bin/ghostty"),  # Homebrew on Apple Silicon
        Path("/usr/local/bin/ghostty"),  # Homebrew on Intel
        Path("/run/current-system/sw/bin/ghostty"),  # Nix
    )
    return any(p.exists() for p in candidates)


def ghostty_installed() -> bool:
    """True if Ghostty is available. Always True in DEV mode (check skipped).

    Detection is deliberately fail-open: a false negative now hard-blocks the TUI
    (see the launch gate), so we accept several independent signals. Crucially, if
    we're already running inside a Ghostty session it counts as installed — this
    covers libghostty-based terminals that ship no ``Ghostty.app`` bundle.
    """
    if is_dev():
        return True
    return is_ghostty_terminal() or shutil.which("ghostty") is not None or _ghostty_app_present()


def should_warn_no_ghostty() -> bool:
    """True if the user should be warned that Ghostty is missing.

    Detection is fail-open (see :func:`ghostty_installed`); the generated
    ``.zshrc`` gate is itself guarded on the Ghostty env signals, so the banner
    just stays dormant until Ghostty is present. Never warns in DEV mode (where
    ``ghostty_installed()`` is forced True anyway).
    """
    return not is_dev() and not ghostty_installed()


def term_program() -> str | None:
    """Value of $TERM_PROGRAM, or None if unset."""
    return os.environ.get("TERM_PROGRAM")


def is_ghostty_terminal() -> bool:
    """True if the current shell is running inside Ghostty.

    ``$TERM_PROGRAM`` alone is fragile — multiplexers (tmux/zellij) and other
    wrappers overwrite it. So we also accept the env vars Ghostty exports
    (``GHOSTTY_RESOURCES_DIR``/``GHOSTTY_BIN_DIR``, which notably survive into tmux
    panes) and its shipped terminfo entry (``TERM=…ghostty``).
    """
    env = os.environ
    return (
        env.get("TERM_PROGRAM") == "ghostty"
        or bool(env.get("GHOSTTY_RESOURCES_DIR"))
        or bool(env.get("GHOSTTY_BIN_DIR"))
        or env.get("TERM", "").endswith("ghostty")
    )
