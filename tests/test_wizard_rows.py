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


async def test_show_all_fonts_toggle_expands_options(fake_home):
    detect.DEV_MODE = True
    from textual.widgets import Select, Switch

    from welchost.tui.fonts import SAFE_FONTS, all_fonts

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        font = app.screen.query_one("#font", Select)
        # _options is a list of (label, value) tuples — stable in this Textual version.
        # default options are the safe set
        assert len(SAFE_FONTS) < len(all_fonts())
        app.screen.query_one("#show-all-fonts", Switch).value = True
        await pilot.pause()
        # after toggling, the option count grows to the full catalogue
        opts_after = [v for _, v in font._options]
        assert len(opts_after) >= len(all_fonts())


async def test_autofit_button_picks_a_fitting_font(fake_home):
    detect.DEV_MODE = True
    from textual.widgets import Button

    from welchost.fit import art_width

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        # Force a wide overflow then auto-fit.
        app.model.banner.rows[0].text = "WELCOME"
        app.model.banner.font = "colossal"
        app.model.banner.fit_width = 40
        app.screen.query_one("#text", Input).value = "WELCOME"
        await pilot.pause()
        app.screen.query_one("#autofit", Button).press()
        await pilot.pause()
        assert art_width(app.model, font=app.model.banner.font) <= 40


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
