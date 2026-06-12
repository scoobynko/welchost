"""The doctor diagnostic must stay hidden from normal users in the TUI too."""

from __future__ import annotations

from welchost import detect
from welchost.tui.screens.main_menu import EditMenu, MainMenu


def _keys(menu) -> list[str]:
    return [key for key, _ in menu.items()]


def test_doctor_absent_from_menus_for_users():
    detect.DEV_MODE = False
    assert "doctor" not in _keys(MainMenu())
    assert "doctor" not in _keys(EditMenu())


def test_doctor_present_in_menus_in_dev():
    detect.DEV_MODE = True
    assert "doctor" in _keys(MainMenu())
    assert "doctor" in _keys(EditMenu())


def test_logo_byline_has_version():
    """The splash byline carries the version, before the 'by scooby' credit."""
    from welchost import __version__
    from welchost.tui.logo import logo_text

    assert f"v{__version__} · by scooby" in logo_text().plain


async def test_esc_on_home_is_noop():
    """esc on the home menu must NOT pop the last screen (no black screen)."""
    from welchost.tui.app import WelchostApp

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.switch_screen(MainMenu())
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)


async def test_byline_visible_on_short_terminal(fake_home):
    """Regression: on a short terminal the EditMenu header was squeezed and the
    'by scooby' byline vanished. It must still render at a small height."""
    import re

    from welchost import detect
    from welchost.config import WelchostConfig, save_config

    detect.DEV_MODE = True
    detect.ensure_config_dir()
    save_config(WelchostConfig.default())

    from welchost.tui.app import WelchostApp

    app = WelchostApp()  # config exists -> EditMenu
    async with app.run_test(size=(90, 28)) as pilot:
        await pilot.pause()
        await pilot.pause()
        chunks = re.findall(r"<text[^>]*>(.*?)</text>", app.export_screenshot(), re.S)
        text = " ".join(re.sub(r"<[^>]+>", "", c) for c in chunks).replace("&#160;", " ")
        assert isinstance(app.screen, EditMenu)
        assert "by scooby" in text


async def test_esc_on_subscreen_goes_back():
    """esc on a pushed sub-screen still pops back to the menu beneath it."""
    from welchost.tui.app import WelchostApp
    from welchost.tui.screens.main_menu import EditCurrentMenu

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.switch_screen(MainMenu())
        await app.push_screen(EditCurrentMenu())
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)
