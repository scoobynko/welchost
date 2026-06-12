"""Template picker — a vertical list with a live preview pane.

Keyboard-only: ↑/↓ to browse (preview updates live), enter to customize the
highlighted template in the wizard (where text/font/etc. are editable).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from ...themes import THEMES, Theme, all_themes
from ..widgets import BannerPreview


class TemplateList(Screen):
    """Pick a template; preview updates as you move the highlight."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    CSS = """
    TemplateList #picker { width: 72; max-width: 100%; padding: 1 2; }
    TemplateList #tpl { height: auto; max-height: 12; border: round $panel; margin: 1 0; }
    TemplateList ListItem { padding: 0 1; }
    TemplateList BannerPreview { margin: 1 0 0 0; }
    """

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="picker"):
                yield Static("~/welchost ❯ pick a template", classes="section-label")
                yield ListView(
                    *[
                        ListItem(Label(f"{t.name}   [dim]{t.blurb}[/dim]"), id=f"tpl-{t.name}")
                        for t in all_themes()
                    ],
                    id="tpl",
                )
                yield Static("live preview", classes="panel-title")
                yield BannerPreview()
                yield Static("↑/↓ browse · enter customize · esc back", classes="hint")
        yield Footer()

    def on_mount(self) -> None:
        lv = self.query_one("#tpl", ListView)
        lv.index = 0
        lv.focus()
        self._apply_current()

    def _theme_from_item(self, item) -> Theme | None:
        if item is None or not item.id:
            return None
        return THEMES.get(item.id[len("tpl-") :])

    def _apply_current(self) -> None:
        lv = self.query_one("#tpl", ListView)
        theme = self._theme_from_item(lv.highlighted_child)
        if theme is None:
            return
        text = self.app.model.banner.text or "Welcome"
        self.app.model = theme.to_config(text=text)
        self.app.refresh_preview()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._apply_current()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Enter -> open the wizard at step 1 so text/font are editable.
        from .wizard import Wizard

        self.app.switch_screen(Wizard(start_step=0))


# Backwards-compatible alias (older imports referenced ThemeGallery).
ThemeGallery = TemplateList
