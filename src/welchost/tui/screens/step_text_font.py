"""Wizard step 1 — text + font + size."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select

from ..fonts import font_options

ALIGNMENTS = ["left", "center", "right"]


class StepTextFont(Vertical):
    """Edits banner.text, banner.font, banner.align live on app.model."""

    title = "Step 1 · text + font + alignment"

    def compose(self) -> ComposeResult:
        # Construct widgets with the model's current values so an allow_blank
        # Select never fires a mount-default Changed that clobbers the model.
        m = self.app.model
        yield Label("banner text", classes="section-label")
        yield Input(m.banner.text, placeholder="Welcome", id="text")
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
        """Font dropdown options, prepending an unknown configured font."""
        opts = font_options()
        if current not in {value for _, value in opts}:
            return [(current, current), *opts]
        return opts

    def load_from_model(self) -> None:
        m = self.app.model
        self.query_one("#text", Input).value = m.banner.text
        self.query_one("#align", Select).value = m.banner.align
        font_select = self.query_one("#font", Select)
        font_select.set_options(self._font_opts(m.banner.font))
        font_select.value = m.banner.font

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "text":
            self.app.model.banner.text = event.value or "Welcome"
            self.app.refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is None:
            return
        if event.select.id == "font":
            self.app.model.banner.font = str(event.value)
            self.app.refresh_preview()
        elif event.select.id == "align":
            self.app.model.banner.align = str(event.value)
            self.app.refresh_preview()
