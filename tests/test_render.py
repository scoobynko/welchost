"""Tests for the Rich render pipeline (multi-row, per-row color)."""

from __future__ import annotations

from welchost.config import Row, SolidColor, WelchostConfig
from welchost.render import render_art


def _one_row(text="Hi", font="standard"):
    cfg = WelchostConfig.default()
    cfg.banner.font = font
    cfg.banner.rows = [Row(text=text)]
    return cfg


def test_two_rows_are_taller_than_one(fake_home):
    one = render_art(_one_row("Hi")).plain.split("\n")
    cfg = _one_row("Hi")
    cfg.banner.rows = [Row(text="Hi"), Row(text="Yo")]
    two = render_art(cfg).plain.split("\n")
    # Two stacked blocks + one blank separator row are strictly taller.
    assert len(two) > len(one)


def test_two_rows_separated_by_blank_line(fake_home):
    cfg = _one_row("Hi")
    cfg.banner.rows = [Row(text="Hi"), Row(text="Yo")]
    lines = render_art(cfg).plain.split("\n")
    assert any(ln.strip() == "" for ln in lines), "expected a blank separator between rows"


def test_each_row_uses_its_own_color(fake_home):
    cfg = _one_row("Hi")
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="red")),
        Row(text="Yo", color_mode="solid", solid=SolidColor(value="blue")),
    ]
    styles = {str(span.style) for span in render_art(cfg).spans}
    # red -> rgb(197,15,31); blue -> rgb(0,55,218) (generator.NAMED_COLORS).
    assert any("197,15,31" in s for s in styles), "row 1 red missing"
    assert any("0,55,218" in s for s in styles), "row 2 blue missing"


def test_single_row_still_renders(fake_home):
    assert render_art(_one_row("Hi")).plain.strip()
