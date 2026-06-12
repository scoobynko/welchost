"""Tests for DEV-mode sandbox isolation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from welchost import detect
from welchost.cli import app

runner = CliRunner()


def test_dev_writes_to_sandbox_not_home(fake_home):
    result = runner.invoke(app, ["--dev", "preview"])
    assert result.exit_code == 0
    # Real config dir under HOME must be untouched.
    real = Path.home() / ".config" / "ghostty" / "welchost.toml"
    assert not real.exists()


def test_dev_install_lands_in_dev_home(fake_home):
    detect.DEV_MODE = True
    from welchost.config import WelchostConfig, save_config
    from welchost.generator import install

    cfg = WelchostConfig.default()
    save_config(cfg)
    install(cfg)
    assert (detect.DEV_HOME / ".config" / "ghostty" / "welchost.toml").exists()
    assert (detect.DEV_HOME / ".zshrc").exists()
    assert not (Path.home() / ".config" / "ghostty" / "welchost.toml").exists()


def test_dev_reset_wipes_dev_home_only(fake_home):
    detect.DEV_MODE = True
    from welchost.config import WelchostConfig, save_config
    from welchost.generator import install, reset

    # A real-home file that must survive a dev reset.
    real_dir = Path.home() / ".config" / "ghostty"
    real_dir.mkdir(parents=True)
    real_marker = real_dir / "welchost.toml"
    real_marker.write_text("# real, do not touch\n")

    save_config(WelchostConfig.default())
    install(WelchostConfig.default())
    assert detect.DEV_HOME.exists()

    reset()
    assert not detect.DEV_HOME.exists()
    assert real_marker.exists()


def test_dev_home_auto_created(fake_home):
    detect.DEV_MODE = True
    assert not detect.DEV_HOME.exists()
    detect.ensure_config_dir()
    assert detect.DEV_HOME.exists()


def test_ghostty_skipped_in_dev(fake_home):
    detect.DEV_MODE = True
    assert detect.ghostty_installed() is True
