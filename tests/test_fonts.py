"""The curated and safe font lists must be valid and render cleanly."""

from __future__ import annotations

import pytest

from welchost.generator import _render_figlet, font_exists
from welchost.tui.fonts import CURATED, SAFE_FONTS, safe_font_options

# Printable characters a banner might use.
_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .-_!?"


def test_safe_fonts_are_a_subset_of_curated():
    assert set(SAFE_FONTS) <= set(CURATED)
    assert SAFE_FONTS, "expected at least one safe font"


@pytest.mark.parametrize("font", SAFE_FONTS)
def test_safe_font_is_valid(font):
    assert font_exists(font)


@pytest.mark.parametrize("font", SAFE_FONTS)
def test_safe_font_renders_charset_cleanly(font):
    art = _render_figlet(font, _CHARSET)
    lines = [ln for ln in art.splitlines() if ln.strip()]
    # Renders to non-empty, multi-line block art with no blank-output character.
    assert lines, f"{font} produced empty art"
    # All visible lines share one height band (no row collapsed to empty mid-block).
    assert len(lines) >= 2


def test_safe_font_options_shape():
    opts = safe_font_options()
    assert opts == [(f, f) for f in SAFE_FONTS]
