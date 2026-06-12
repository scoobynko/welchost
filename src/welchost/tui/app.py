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
    #menu-box, #wizard-body { width: 72; max-width: 100%; padding: 1 2; }
    .panel-title { text-style: bold; padding: 1 0 0 1; color: $text-muted; }
    .hint { color: $text-muted; padding: 1 2; }
    .section-label { text-style: bold; padding: 1 0 0 0; }
    ListView { padding: 0; margin: 1 0; }
    ListItem { padding: 0 1; }
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

    # --- config lifecycle ----------------------------------------------------
    # `model` is the working config; `had_config` tracks whether a config exists
    # on disk. These three helpers are the only places that mutate that pair, so
    # the state stays consistent across save / delete / new-build flows.

    def adopt_config(self, model: WelchostConfig) -> None:
        """Record `model` as the now-installed config (call after a save)."""
        self.model = model
        self.had_config = True

    def clear_config(self) -> None:
        """Reset to defaults with nothing installed (call after delete/reset)."""
        self.model = WelchostConfig.default()
        self.had_config = False

    def new_draft(self) -> None:
        """Start a fresh in-memory config for a new build. The on-disk files are
        untouched until the user saves, so `had_config` is intentionally left as
        is rather than flipped — it reflects disk, not the editor."""
        self.model = WelchostConfig.default()

    def refresh_preview(self) -> None:
        """Re-render every mounted BannerPreview from the current model.

        Queries the active screen, not the app: in Textual 8.x ``App.query``
        does not descend into the current screen's tree, so ``self.query`` here
        would match nothing and the preview would never render.
        """
        for preview in self.screen.query(BannerPreview):
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
