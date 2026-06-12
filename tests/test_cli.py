"""Tests for the CLI commands via Typer's CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from welchost import __version__, detect
from welchost.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "welchost" in result.stdout
    assert __version__ in result.stdout


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("config", "preview", "reset", "version"):
        assert cmd in result.stdout


def test_doctor_hidden_from_user_help():
    """doctor is a dev-only diagnostic and must not appear in the public CLI."""
    result = runner.invoke(app, ["--help"])
    assert "doctor" not in result.stdout


def test_preview_without_config(fake_home):
    result = runner.invoke(app, ["--dev", "preview"])
    assert result.exit_code == 0
    assert "No config found" in result.stdout


def test_preview_with_config(fake_home):
    detect.DEV_MODE = True
    from welchost.config import save_config
    from welchost.themes import get_theme

    save_config(get_theme("ghost").to_config(text="Yo"))
    detect.DEV_MODE = False
    result = runner.invoke(app, ["--dev", "preview"])
    assert result.exit_code == 0
    assert "No config found" not in result.stdout


def test_doctor_runs(fake_home):
    result = runner.invoke(app, ["--dev", "doctor"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout.lower()


def test_doctor_blocked_without_dev(fake_home):
    """A normal user invoking doctor is refused, not given diagnostics."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code != 0
    assert "development-only" in result.stdout


def test_reset_aborts_on_no(fake_home):
    result = runner.invoke(app, ["--dev", "reset"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted" in result.stdout


def test_reset_yes_flag(fake_home):
    result = runner.invoke(app, ["--dev", "reset", "--yes"])
    assert result.exit_code == 0


def test_reset_removes_installed_files(fake_home):
    detect.DEV_MODE = True
    from welchost.config import WelchostConfig, save_config
    from welchost.generator import install

    save_config(WelchostConfig.default())
    install(WelchostConfig.default())
    detect.DEV_MODE = False

    result = runner.invoke(app, ["--dev", "reset", "--yes"])
    assert result.exit_code == 0
    assert not detect.DEV_HOME.exists()
