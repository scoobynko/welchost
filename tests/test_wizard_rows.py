"""Wizard support for a second stacked row."""

from __future__ import annotations

from textual.widgets import Input

from welchost import detect
from welchost.tui.app import WelchostApp
from welchost.tui.screens.wizard import Wizard


async def test_typing_second_row_adds_a_row(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.query_one("#text2", Input).value = "SALMIK"
        await pilot.pause()
        assert len(app.model.banner.rows) == 2
        assert app.model.banner.rows[1].text == "SALMIK"


async def test_clearing_second_row_trims_back_to_one(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        text2 = app.screen.query_one("#text2", Input)
        text2.value = "SALMIK"
        await pilot.pause()
        text2.value = ""
        await pilot.pause()
        assert len(app.model.banner.rows) == 1


async def test_second_row_color_is_independent(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        # Add a second row in step 1.
        app.screen.query_one("#text2", Input).value = "SALMIK"
        await pilot.pause()
        # Move to step 2 (color).
        app.screen.action_next()
        await pilot.pause()
        from welchost.tui.widgets import ColorField

        app.screen.query_one("#solid-0", ColorField).set_value("red")
        app.screen.query_one("#solid-1", ColorField).set_value("blue")
        await pilot.pause()
        assert app.model.banner.rows[0].solid.value == "red"
        assert app.model.banner.rows[1].solid.value == "blue"


async def test_row2_color_group_hidden_with_one_row(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.action_next()  # step 2 with a single row
        await pilot.pause()
        assert app.screen.query_one("#row-1-group").display is False


async def test_font_picker_offers_full_catalog_curated_first(fake_home):
    # The picker offers every pyfiglet font (curated first) — width safety is
    # handled under the hood on save, so the choice needn't be restricted.
    detect.DEV_MODE = True
    from textual.widgets import Select

    from welchost.tui.fonts import CURATED, all_fonts

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        font = app.screen.query_one("#font", Select)
        opts = [v for _, v in font._options]
        assert len(opts) == len(all_fonts())  # the whole catalogue
        assert opts[0] == CURATED[0]  # curated surfaced first
        assert "isometric1" in opts  # a cool non-"safe" font is available again


async def test_unknown_configured_font_stays_selectable(fake_home):
    # Robustness / escape hatch: a font name not in the catalogue (e.g. a typo or
    # removed font in a hand-edited welchost.toml) is prepended so it isn't lost.
    detect.DEV_MODE = True
    from textual.widgets import Select

    app = WelchostApp()
    async with app.run_test() as pilot:
        app.model.banner.font = "not-a-real-font"
        await app.push_screen(Wizard())
        await pilot.pause()
        font = app.screen.query_one("#font", Select)
        opts = [v for _, v in font._options]
        assert opts[0] == "not-a-real-font"
        assert font.value == "not-a-real-font"


async def test_autofit_on_save_shrinks_overflowing_font(fake_home):
    # Width-safety is now under the hood: on save, an overflowing banner is
    # silently swapped to the largest safe font that fits — no visible control.
    detect.DEV_MODE = True
    from welchost.fit import fits

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        m = app.model
        m.banner.rows[0].text = "WELCOME"
        m.banner.font = "colossal"  # a safe font, but wide enough to overflow
        m.banner.fit_width = 40
        assert not fits(m)  # precondition: overflows the target
        confirm = app.screen.steps[3]  # StepConfirm
        confirm._apply_autofit()
        assert fits(m)  # now fits, silently


async def test_metadata_controls_mutate_model(fake_home):
    detect.DEV_MODE = True
    from textual.widgets import Input, Select

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.action_next()  # step 2
        app.screen.action_next()  # step 3 (decoration + info)
        await pilot.pause()
        app.screen.query_one("#info-layout", Select).value = "stacked"
        app.screen.query_one("#info-separator", Input).value = "|"
        app.screen.query_one("#info-accent", Input).value = "#ff0000"
        await pilot.pause()
        assert app.model.info.layout == "stacked"
        assert app.model.info.separator == "|"
        assert app.model.info.accent == "#ff0000"
