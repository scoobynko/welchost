"""Tests for config load/save and round-trip."""

from __future__ import annotations

from welchost import detect
from welchost.config import WelchostConfig, load_config, save_config


def test_load_missing_returns_none(fake_home):
    assert load_config() is None


def test_save_then_load_roundtrip(fake_home):
    cfg = WelchostConfig.default()
    cfg.banner.text = "Hi there"
    cfg.banner.font = "doom"
    cfg.banner.color_mode = "gradient"
    cfg.gradient.start = "#ff6b35"
    cfg.gradient.end = "#f7c59f"
    cfg.decoration.border_style = "double"
    cfg.info.show_python = True
    cfg.info.show_user = False
    save_config(cfg)

    loaded = load_config()
    assert loaded is not None
    assert loaded.banner.text == "Hi there"
    assert loaded.banner.font == "doom"
    assert loaded.banner.color_mode == "gradient"
    assert loaded.gradient.start == "#ff6b35"
    assert loaded.gradient.end == "#f7c59f"
    assert loaded.decoration.border_style == "double"
    assert loaded.info.show_python is True
    assert loaded.info.show_user is False


def test_save_stamps_created_at_and_version(fake_home):
    cfg = WelchostConfig.default()
    assert cfg.meta.created_at == ""
    save_config(cfg)
    loaded = load_config()
    assert loaded.meta.created_at != ""
    assert loaded.meta.welchost_version


def test_save_creates_config_dir(fake_home):
    assert not detect.get_config_dir().exists()
    save_config(WelchostConfig.default())
    assert detect.get_config_path().exists()


def test_defaults_match_schema(fake_home):
    cfg = WelchostConfig.default()
    assert cfg.banner.text == "Welcome"
    assert cfg.banner.font == "slant"
    assert cfg.banner.size == "auto"
    assert cfg.banner.color_mode == "solid"
    assert cfg.solid.value == "cyan"
    assert cfg.decoration.border_style == "panel"
