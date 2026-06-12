"""Tests for path resolution and environment detection."""

from __future__ import annotations

from pathlib import Path

from welchost import detect


def test_config_dir_uses_xdg(fake_home, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))
    assert detect.get_config_dir() == fake_home / ".config" / "ghostty"


def test_config_dir_falls_back_to_home(fake_home, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert detect.get_config_dir() == Path.home() / ".config" / "ghostty"


def test_zshrc_is_in_home(fake_home):
    assert detect.get_zshrc() == Path.home() / ".zshrc"


def test_dev_mode_paths(fake_home):
    detect.DEV_MODE = True
    assert detect.get_config_dir() == detect.DEV_HOME / ".config" / "ghostty"
    assert detect.get_zshrc() == detect.DEV_HOME / ".zshrc"


def test_ghostty_installed_true_in_dev(fake_home):
    detect.DEV_MODE = True
    assert detect.ghostty_installed() is True


def test_is_dev_honors_env(fake_home, monkeypatch):
    assert detect.is_dev() is False
    monkeypatch.setenv("WELCHOST_DEV", "1")
    assert detect.is_dev() is True


def test_ensure_config_dir_creates(fake_home):
    detect.DEV_MODE = True
    d = detect.ensure_config_dir()
    assert d.exists() and d.is_dir()
