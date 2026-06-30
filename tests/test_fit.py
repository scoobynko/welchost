"""Width measurement and auto-fit font selection."""

from __future__ import annotations

from welchost.config import Row, WelchostConfig
from welchost.fit import art_width, auto_fit_font, fits


def _cfg(text="Hi", font="standard"):
    cfg = WelchostConfig.default()
    cfg.banner.font = font
    cfg.banner.rows = [Row(text=text)]
    return cfg


def test_art_width_positive_and_ornament_adds_width():
    cfg = _cfg("Hi")
    base = art_width(cfg)
    assert base > 0
    cfg.ornament.name = "ghosts"
    assert art_width(cfg) > base


def test_art_width_font_override():
    cfg = _cfg("WELCOME", font="standard")
    narrow = art_width(cfg, font="standard")
    wide = art_width(cfg, font="colossal")
    assert wide > narrow


def test_fits_respects_target():
    cfg = _cfg("Hi")
    cfg.banner.fit_width = 5
    assert fits(cfg) is False
    cfg.banner.fit_width = 1000
    assert fits(cfg) is True
    cfg.banner.fit_width = 0  # disabled
    assert fits(cfg) is True


def test_auto_fit_picks_a_fitting_font_when_one_exists():
    cfg = _cfg("WELCOME", font="colossal")
    cfg.banner.fit_width = 48
    candidates = ["colossal", "big", "standard", "slant"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen in candidates
    # The chosen font actually fits the target.
    assert art_width(cfg, font=chosen) <= 48


def test_auto_fit_returns_widest_when_target_disabled():
    cfg = _cfg("WELCOME")
    cfg.banner.fit_width = 0
    candidates = ["standard", "colossal"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen == "colossal"  # widest


def test_auto_fit_least_overflow_when_none_fit():
    cfg = _cfg("WELCOME")
    cfg.banner.fit_width = 1  # impossibly small
    candidates = ["standard", "colossal"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen == "standard"  # least overflow
