"""Tests for the 12 built-in themes."""

from __future__ import annotations

import pytest
from pyfiglet import Figlet

from welchost.themes import THEMES, all_themes, get_theme

EXPECTED = {
    "ghost",
    "hacker",
    "dracula",
    "catppuccin",
    "nord",
    "gruvbox",
    "tokyo-night",
    "monochrome",
    "hot",
    "ocean",
    "matrix",
    "sunset",
}


def test_all_twelve_themes_present():
    assert set(THEMES) == EXPECTED
    assert len(all_themes()) == 12


@pytest.mark.parametrize("theme", all_themes(), ids=lambda t: t.name)
def test_theme_font_is_valid_pyfiglet(theme):
    # Raises FontNotFound if the font name is invalid.
    fig = Figlet(font=theme.font)
    assert fig.renderText("Ab").strip()


@pytest.mark.parametrize("theme", all_themes(), ids=lambda t: t.name)
def test_theme_converts_to_config(theme):
    cfg = theme.to_config(text="Hi")
    assert cfg.banner.text == "Hi"
    assert cfg.banner.font == theme.font
    assert cfg.decoration.border_style == theme.border_style
    if theme.is_gradient:
        assert cfg.banner.color_mode == "gradient"
    else:
        assert cfg.banner.color_mode == "solid"


def test_sunset_is_gradient():
    sunset = get_theme("sunset")
    assert sunset is not None
    assert sunset.is_gradient
    cfg = sunset.to_config()
    assert cfg.gradient.start == "#ff6b35"
    assert cfg.gradient.end == "#f7c59f"


def test_get_unknown_theme_returns_none():
    assert get_theme("nope") is None
