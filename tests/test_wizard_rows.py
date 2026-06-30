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
