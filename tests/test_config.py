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
    cfg.gradient.direction = "diagonal"
    cfg.decoration.border_style = "double"
    cfg.ornament.name = "ghosts"
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
    assert loaded.gradient.direction == "diagonal"
    assert loaded.decoration.border_style == "double"
    assert loaded.ornament.name == "ghosts"
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


def test_legacy_size_key_is_ignored(fake_home):
    # Old welchost.toml files carried a now-removed `banner.size`; loading must
    # not crash and should fall back to the default align.
    cfg = WelchostConfig.from_toml_dict(
        {"banner": {"text": "Hi", "font": "slant", "size": "xl", "color_mode": "solid"}}
    )
    assert cfg.banner.text == "Hi"
    assert cfg.banner.align == "left"
    assert not hasattr(cfg.banner, "size")


def test_defaults_match_schema(fake_home):
    cfg = WelchostConfig.default()
    assert cfg.banner.text == "Welcome"
    assert cfg.banner.font == "slant"
    assert cfg.banner.align == "left"
    assert cfg.banner.color_mode == "solid"
    assert cfg.solid.value == "cyan"
    assert cfg.gradient.direction == "horizontal"
    assert cfg.decoration.border_style == "none"
    assert cfg.ornament.name == "none"
    # Only user + date/time default on; the rest are off and wizard-hidden.
    assert cfg.info.show_user is True
    assert cfg.info.show_datetime is True
    assert cfg.info.show_host is False
    assert cfg.info.show_os is False
