"""Template picker — a vertical list with a live preview pane.

Keyboard-only: ↑/↓ to browse (preview updates live), enter to customize the
highlighted template in the wizard (where text/font/etc. are editable).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from ...themes import THEMES, Theme, all_themes
from ..widgets import BannerPreview


class TemplateList(Screen):
    """Pick a template; preview updates as you move the highlight."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    CSS = """
    TemplateList #picker { width: 100%; height: 1fr; }
    /* List on the left, live preview on the right, each scrolls on its own. */
    TemplateList #list-col { width: 56; max-width: 60%; padding: 1 2; height: 1fr; }
    TemplateList #preview-col { width: 1fr; padding: 1 2; height: 1fr; border-left: round $panel; }
    TemplateList #tpl { height: auto; border: round $panel; margin: 1 0; }
    TemplateList ListItem { padding: 0 1; }
    TemplateList BannerPreview { margin: 1 0 0 0; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="picker"):
            with Vertical(id="list-col"):
                yield Static("~/welchost ❯ pick a template", classes="section-label")
                yield ListView(
                    *[
                        ListItem(Label(f"{t.name}   [dim]{t.blurb}[/dim]"), id=f"tpl-{t.name}")
                        for t in all_themes()
                    ],
                    id="tpl",
                )
                yield Static("↑/↓ browse · enter customize · esc back", classes="hint")
            with VerticalScroll(id="preview-col"):
                yield Static("live preview", classes="panel-title")
                yield BannerPreview()
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
