"""Tests for the self-update logic (pure: no real network or subprocess)."""

from __future__ import annotations

import sys

import pytest

from welchost import __version__, update


@pytest.mark.parametrize(
    "latest,current,expected",
    [
        ("1.0.3", "1.0.2", True),
        ("1.0.2", "1.0.2", False),
        ("1.0.1", "1.0.2", False),
        ("1.1.0", "1.0.9", True),
        ("2.0.0", "1.9.9", True),
        ("1.0.10", "1.0.9", True),  # numeric compare, not lexical
    ],
)
def test_is_newer(latest, current, expected):
    assert update.is_newer(latest, current) is expected


def test_parse_is_numeric():
    assert update._parse("1.0.2") == (1, 0, 2)
    assert update._parse("1.2") == (1, 2)


def test_current_version_matches_package():
    assert update.current_version() == __version__


def test_upgrade_command_per_method():
    assert update.upgrade_command("brew") == ["brew", "upgrade", "welchost"]
    assert update.upgrade_command("pipx") == ["pipx", "upgrade", "welchost"]
    pip = update.upgrade_command("pip")
    assert pip[0] == sys.executable and pip[-1] == "welchost" and "--upgrade" in pip


def test_detect_install_method_is_known():
    assert update.detect_install_method() in {"brew", "pipx", "pip"}


def test_latest_version_returns_none_when_offline(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    assert update.latest_version(timeout=0.1) is None


async def test_update_prompt_shows_modal(fake_home, monkeypatch):
    """When a newer version is detected, the launch flow offers a yes/no modal."""
    # Stub the network so the on-mount check does nothing real.
    monkeypatch.setattr(update, "latest_version", lambda *a, **k: None)

    from welchost.tui.app import WelchostApp
    from welchost.tui.screens.modals import ConfirmModal

    app = WelchostApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._prompt_update("99.0.0")  # as if a newer version was found
        await pilot.pause()
        assert isinstance(app.screen, ConfirmModal)
