"""Tests for config load/save, round-trip, and legacy migration."""

from __future__ import annotations

from welchost import detect
from welchost.config import (
    GradientColor,
    Row,
    SolidColor,
    WelchostConfig,
    load_config,
    save_config,
)


def test_load_missing_returns_none(fake_home):
    assert load_config() is None


def test_default_has_single_row(fake_home):
    cfg = WelchostConfig.default()
    assert len(cfg.banner.rows) == 1
    assert cfg.banner.rows[0].text == "Welcome"
    assert cfg.banner.rows[0].color_mode == "solid"
    assert cfg.banner.font == "slant"
    assert cfg.banner.align == "left"
    assert cfg.banner.fit_width == 80


def test_two_row_roundtrip_is_lossless(fake_home):
    cfg = WelchostConfig.default()
    cfg.banner.font = "ansi_shadow"
    cfg.banner.rows = [
        Row(text="JAKUB", color_mode="solid", solid=SolidColor(value="#d97757")),
        Row(
            text="SALMIK",
            color_mode="gradient",
            gradient=GradientColor(start="cyan", end="magenta", direction="horizontal"),
        ),
    ]
    save_config(cfg)

    loaded = load_config()
    assert loaded is not None
    assert loaded.banner.font == "ansi_shadow"
    assert [r.text for r in loaded.banner.rows] == ["JAKUB", "SALMIK"]
    assert loaded.banner.rows[0].color_mode == "solid"
    assert loaded.banner.rows[0].solid.value == "#d97757"
    assert loaded.banner.rows[1].color_mode == "gradient"
    assert loaded.banner.rows[1].gradient.start == "cyan"
    assert loaded.banner.rows[1].gradient.end == "magenta"
    assert loaded.banner.rows[1].gradient.direction == "horizontal"


def test_legacy_flat_config_migrates_to_one_row(fake_home):
    # A pre-2.0 welchost.toml: text + color_mode on [banner], color in [color.*].
    legacy = {
        "banner": {"text": "Hi there", "font": "doom", "align": "center", "color_mode": "gradient"},
        "color": {
            "solid": {"value": "cyan"},
            "gradient": {"start": "#ff6b35", "end": "#f7c59f", "direction": "diagonal"},
        },
    }
    cfg = WelchostConfig.from_toml_dict(legacy)
    assert cfg.banner.font == "doom"
    assert cfg.banner.align == "center"
    assert len(cfg.banner.rows) == 1
    row = cfg.banner.rows[0]
    assert row.text == "Hi there"
    assert row.color_mode == "gradient"
    assert row.gradient.start == "#ff6b35"
    assert row.gradient.end == "#f7c59f"
    assert row.gradient.direction == "diagonal"


def test_legacy_size_key_is_ignored(fake_home):
    # The long-removed `banner.size` must not crash the loader.
    cfg = WelchostConfig.from_toml_dict(
        {"banner": {"text": "Hi", "font": "slant", "size": "xl", "color_mode": "solid"}}
    )
    assert cfg.banner.rows[0].text == "Hi"
    assert cfg.banner.align == "left"
    assert not hasattr(cfg.banner, "size")


def test_save_stamps_created_at_and_version(fake_home):
    cfg = WelchostConfig.default()
    assert cfg.meta.created_at == ""
    save_config(cfg)
    loaded = load_config()
    assert loaded.meta.created_at != ""
    assert loaded.meta.welchost_version == "2.0.0"


def test_save_creates_config_dir(fake_home):
    assert not detect.get_config_dir().exists()
    save_config(WelchostConfig.default())
    assert detect.get_config_path().exists()


def test_info_styling_fields_default(fake_home):
    info = WelchostConfig.default().info
    assert info.layout == "inline"
    assert info.separator == "·"
    assert info.accent == "auto"


def test_info_styling_roundtrip(fake_home):
    cfg = WelchostConfig.default()
    cfg.info.layout = "stacked"
    cfg.info.separator = "|"
    cfg.info.accent = "#ff0000"
    save_config(cfg)
    loaded = load_config()
    assert loaded is not None
    assert loaded.info.layout == "stacked"
    assert loaded.info.separator == "|"
    assert loaded.info.accent == "#ff0000"


def test_decoration_ornament_info_roundtrip(fake_home):
    cfg = WelchostConfig.default()
    cfg.decoration.border_style = "double"
    cfg.decoration.border_color = "#ff0000"
    cfg.ornament.name = "ghosts"
    cfg.info.show_python = True
    cfg.info.show_user = False
    save_config(cfg)
    loaded = load_config()
    assert loaded is not None
    assert loaded.decoration.border_style == "double"
    assert loaded.decoration.border_color == "#ff0000"
    assert loaded.ornament.name == "ghosts"
    assert loaded.info.show_python is True
    assert loaded.info.show_user is False
