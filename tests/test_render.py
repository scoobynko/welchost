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


def _info_cfg(layout="inline"):
    from welchost.config import Row, SolidColor

    cfg = WelchostConfig.default()
    cfg.banner.rows = [Row(text="Hi", color_mode="solid", solid=SolidColor(value="#3a96dd"))]
    cfg.decoration.border_style = "none"
    cfg.info.show_user = True
    cfg.info.show_datetime = False
    cfg.info.show_host = True
    cfg.info.layout = layout
    cfg.info.separator = "·"
    cfg.info.accent = "#d97757"
    return cfg


def test_info_inline_is_single_line_with_accent_and_separator(fake_home):
    import getpass

    from welchost.render import info_text

    t = info_text(_info_cfg("inline"))
    assert t is not None
    assert "\n" not in t.plain  # single inline line
    assert "·" in t.plain  # separator between the two items
    # No "user "/"host " label prefixes — just the values.
    assert t.plain.startswith(getpass.getuser())
    assert "user " not in t.plain
    assert "host " not in t.plain
    styles = {str(s.style) for s in t.spans}
    # Accent (terracotta #d97757 -> 217,119,87) still colours the separators.
    assert any("217,119,87" in s for s in styles)


def test_info_stacked_is_multiline_values_only(fake_home):
    import getpass

    from welchost.render import info_text

    t = info_text(_info_cfg("stacked"))
    assert t is not None
    assert "\n" in t.plain  # one line per item
    assert "user: " not in t.plain  # labels dropped here too
    assert getpass.getuser() in t.plain
    # values carry the banner color (#3a96dd -> 58,150,221), not default white
    styles = {str(s.style) for s in t.spans}
    assert any("58,150,221" in s for s in styles)
