"""Wizard step 1 — text + font + size."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, ListItem, ListView, Select

from ..fonts import search_fonts

SIZES = ["auto", "sm", "md", "lg", "xl"]


class StepTextFont(Vertical):
    """Edits banner.text, banner.font, banner.size live on app.model."""

    title = "Step 1 · text + font + size"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._fonts: list[str] = []

    def compose(self) -> ComposeResult:
        yield Label("Banner text")
        yield Input(placeholder="Welcome", id="text")
        yield Label("Font  (type to search 571 fonts; blank = curated)")
        yield Input(placeholder="search fonts…", id="font_search")
        yield ListView(id="font_list")
        yield Label("Size")
        yield Select([(s, s) for s in SIZES], id="size", allow_blank=False)

    def load_from_model(self) -> None:
        m = self.app.model
        self.query_one("#text", Input).value = m.banner.text
        self.query_one("#size", Select).value = m.banner.size
        self._populate_fonts("", select=m.banner.font)

    def _populate_fonts(self, query: str, select: str | None = None) -> None:
        lv = self.query_one("#font_list", ListView)
        lv.clear()
        fonts = search_fonts(query)
        if select and select not in fonts:
            fonts = [select, *fonts]
        self._fonts = fonts
        # No per-item IDs: font names can repeat across re-populations and the
        # async clear()/append cycle would otherwise raise DuplicateIds.
        for f in fonts:
            lv.append(ListItem(Label(f)))
        if select and select in fonts:
            lv.index = fonts.index(select)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "text":
            self.app.model.banner.text = event.value or "Welcome"
            self.app.refresh_preview()
        elif event.input.id == "font_search":
            self._populate_fonts(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None or not (0 <= idx < len(self._fonts)):
            return
        self.app.model.banner.font = self._fonts[idx]
        self.app.refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "size" and event.value is not None:
            self.app.model.banner.size = str(event.value)
            self.app.refresh_preview()
