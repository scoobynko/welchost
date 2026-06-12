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
