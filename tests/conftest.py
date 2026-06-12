"""Shared pytest fixtures.

Every test runs against a throwaway HOME so nothing touches the real config or
~/.zshrc. DEV_MODE is reset around each test.
"""

from __future__ import annotations

import pytest

from welchost import detect


@pytest.fixture(autouse=True)
def reset_dev_mode():
    """Ensure DEV_MODE starts False and is restored after each test."""
    detect.DEV_MODE = False
    yield
    detect.DEV_MODE = False


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect HOME + XDG_CONFIG_HOME to a tmp dir and cwd into it.

    Normal-mode paths resolve under tmp_path; DEV-mode dev-home/ lands under the
    tmp cwd. Either way the real home is never touched.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.delenv("WELCHOST_DEV", raising=False)
    monkeypatch.chdir(tmp_path)
    return home
