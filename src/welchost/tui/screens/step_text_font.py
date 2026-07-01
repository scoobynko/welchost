"""Wizard step 1 — stacked text rows + shared font + alignment.

The font picker offers the whole pyfiglet catalogue (curated first, type-to-jump);
width-safety is applied under the hood on save (see StepConfirm._apply_autofit),
so the choice needn't be restricted. A font that fits is kept as picked; only an
overflowing one is silently swapped on save.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select

from ...config import Row
from ..fonts import font_options

ALIGNMENTS = ["left", "center", "right"]


class StepTextFont(Vertical):
    """Edits the row texts and the shared banner.font/align on app.model."""

    title = "Step 1 · text + font + alignment"

    def compose(self) -> ComposeResult:
        m = self.app.model
        rows = m.banner.rows
        yield Label("banner text", classes="section-label")
        yield Input(rows[0].text, placeholder="Welcome", id="text")
        yield Label("second row  (optional · leave blank for one line)", classes="section-label")
        yield Input(rows[1].text if len(rows) > 1 else "", placeholder="(none)", id="text2")
        yield Label("font  (type to jump · curated first)", classes="section-label")
        yield Select(
            self._font_opts(m.banner.font), id="font", value=m.banner.font, allow_blank=False
        )
        yield Label("alignment  (position on screen)", classes="section-label")
        yield Select(
            [(a, a) for a in ALIGNMENTS], id="align", value=m.banner.align, allow_blank=False
        )

    @staticmethod
    def _font_opts(current: str) -> list[tuple[str, str]]:
        """The whole pyfiglet catalogue, curated first. A configured font name
        that isn't in the catalogue (a typo or removed font in a hand-edited
        welchost.toml) is prepended so it stays selectable rather than dropped."""
        opts = font_options()
        if current not in {value for _, value in opts}:
            return [(current, current), *opts]
        return opts

    def load_from_model(self) -> None:
        m = self.app.model
        rows = m.banner.rows
        self.query_one("#text", Input).value = rows[0].text
        self.query_one("#text2", Input).value = rows[1].text if len(rows) > 1 else ""
        self.query_one("#align", Select).value = m.banner.align
        font_select = self.query_one("#font", Select)
        font_select.set_options(self._font_opts(m.banner.font))
        font_select.value = m.banner.font

    def on_input_changed(self, event: Input.Changed) -> None:
        rows = self.app.model.banner.rows
        if event.input.id == "text":
            rows[0].text = event.value or "Welcome"
        elif event.input.id == "text2":
            self._set_second_row(event.value)
        self.app.refresh_preview()

    def _set_second_row(self, text: str) -> None:
        rows = self.app.model.banner.rows
        if text.strip():
            if len(rows) > 1:
                rows[1].text = text
            else:
                rows.append(Row(text=text))
        elif len(rows) > 1:
            del rows[1:]

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is None:
            return
        if event.select.id == "font":
            self.app.model.banner.font = str(event.value)
            self.app.refresh_preview()
        elif event.select.id == "align":
            self.app.model.banner.align = str(event.value)
            self.app.refresh_preview()
