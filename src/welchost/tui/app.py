"""Textual application entry point for welchost."""

from __future__ import annotations

from textual.app import App

from .. import detect
from ..config import WelchostConfig, load_config
from .widgets import BannerPreview


class WelchostApp(App):
    """The welchost TUI.

    Holds a single working :class:`WelchostConfig` (``self.model``) that every
    screen mutates and previews live.
    """

    TITLE = "welchost"
    SUB_TITLE = "a welcome screen for Ghostty"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    CSS = """
    Screen { align: center top; }
    .panel-title { text-style: bold; padding: 1 0 0 1; }
    .hint { color: $text-muted; padding: 0 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        loaded = load_config()
        self.had_config: bool = loaded is not None
        self.model: WelchostConfig = loaded or WelchostConfig.default()

    def on_mount(self) -> None:
        from .screens.main_menu import MainMenu

        if self.had_config:
            from .screens.main_menu import EditMenu

            self.push_screen(EditMenu())
        else:
            self.push_screen(MainMenu())

    def refresh_preview(self) -> None:
        """Re-render every mounted BannerPreview from the current model."""
        for preview in self.query(BannerPreview):
            preview.show(self.model)


def run() -> None:
    """Launch the app (starts the dev hot-reload watcher in DEV mode)."""
    if detect.is_dev():
        try:
            from .dev_watcher import start_watcher

            start_watcher()
        except Exception:
            pass
    WelchostApp().run()
