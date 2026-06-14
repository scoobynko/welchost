"""Self-update checks: is a newer welchost on PyPI, and how to upgrade.

Pure core (no TUI, no Textual). The TUI calls these from a background thread on
launch and, if a newer version exists, prompts the user to update. Everything
here fails soft — a network hiccup must never break or delay the app, so
:func:`latest_version` returns ``None`` on any error rather than raising.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import __version__, net

PYPI_JSON = "https://pypi.org/pypi/welchost/json"


def current_version() -> str:
    return __version__


def latest_version(timeout: float = 2.0) -> str | None:
    """Latest welchost version on PyPI, or ``None`` on any failure (offline,
    timeout, malformed response). Never raises."""
    try:
        with urllib.request.urlopen(PYPI_JSON, timeout=timeout, context=net.ssl_context()) as resp:  # noqa: S310
            data = json.load(resp)
        version = data["info"]["version"]
        return version if isinstance(version, str) else None
    except Exception:
        return None


def _parse(v: str) -> tuple[int, ...]:
    """Lenient numeric version tuple: '1.0.2' -> (1, 0, 2). Non-numeric suffixes
    on a part (e.g. '2rc1') are truncated to their leading digits."""
    out: list[int] = []
    for part in v.split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        out.append(int(digits) if digits else 0)
    return tuple(out)


def is_newer(latest: str, current: str) -> bool:
    """True iff ``latest`` is a strictly higher release than ``current``."""
    try:
        return _parse(latest) > _parse(current)
    except Exception:
        return False


def detect_install_method() -> str:
    """How welchost is installed: ``brew`` | ``pipx`` | ``pip``.

    Inferred from the running interpreter's prefix and the resolved executable
    path. Defaults to ``pip`` when nothing more specific matches.
    """
    blob = f"{Path(sys.prefix).resolve()} {shutil.which('welchost') or ''}".lower()
    if "/cellar/welchost" in blob:
        return "brew"
    if "pipx" in blob:
        return "pipx"
    return "pip"


def upgrade_command(method: str) -> list[str]:
    """The shell command that upgrades welchost for the given install method."""
    if method == "brew":
        return ["brew", "upgrade", "welchost"]
    if method == "pipx":
        return ["pipx", "upgrade", "welchost"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", "welchost"]


def run_upgrade(method: str, timeout: float = 300.0) -> tuple[bool, str]:
    """Run the upgrade command. Returns ``(succeeded, combined_output)``."""
    cmd = upgrade_command(method)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "upgrade timed out"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)
