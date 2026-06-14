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


def test_is_ghostty_terminal_via_term_program(fake_home, monkeypatch):
    monkeypatch.setenv("TERM_PROGRAM", "ghostty")
    assert detect.is_ghostty_terminal() is True


def test_is_ghostty_terminal_via_resources_dir_under_tmux(fake_home, monkeypatch):
    # tmux rewrites TERM_PROGRAM to "tmux", but GHOSTTY_RESOURCES_DIR survives.
    monkeypatch.setenv("TERM_PROGRAM", "tmux")
    monkeypatch.setenv("GHOSTTY_RESOURCES_DIR", "/Applications/Ghostty.app/…/ghostty")
    assert detect.is_ghostty_terminal() is True


def test_is_ghostty_terminal_via_term(fake_home, monkeypatch):
    for v in ("TERM_PROGRAM", "GHOSTTY_RESOURCES_DIR", "GHOSTTY_BIN_DIR"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("TERM", "xterm-ghostty")
    assert detect.is_ghostty_terminal() is True


def test_is_ghostty_terminal_false_when_no_signals(fake_home, monkeypatch):
    for v in ("TERM_PROGRAM", "GHOSTTY_RESOURCES_DIR", "GHOSTTY_BIN_DIR"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert detect.is_ghostty_terminal() is False


def test_ghostty_installed_true_when_in_ghostty_terminal(fake_home, monkeypatch):
    # A libghostty-based terminal: no Ghostty.app, no `ghostty` on PATH, but we're
    # clearly running in a Ghostty session — so it must count as installed.
    monkeypatch.setattr(detect, "is_ghostty_terminal", lambda: True)
    monkeypatch.setattr(detect, "_ghostty_app_present", lambda: False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert detect.ghostty_installed() is True


def test_ghostty_installed_false_when_no_signals(fake_home, monkeypatch):
    monkeypatch.setattr(detect, "is_ghostty_terminal", lambda: False)
    monkeypatch.setattr(detect, "_ghostty_app_present", lambda: False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert detect.ghostty_installed() is False


def test_should_warn_no_ghostty_when_missing(fake_home, monkeypatch):
    monkeypatch.setattr(detect, "ghostty_installed", lambda: False)
    assert detect.should_warn_no_ghostty() is True


def test_should_warn_no_ghostty_false_when_installed(fake_home, monkeypatch):
    monkeypatch.setattr(detect, "ghostty_installed", lambda: True)
    assert detect.should_warn_no_ghostty() is False


def test_should_warn_no_ghostty_false_in_dev(fake_home):
    detect.DEV_MODE = True
    assert detect.should_warn_no_ghostty() is False
