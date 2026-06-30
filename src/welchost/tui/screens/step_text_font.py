"""Wizard step 1 — stacked text rows + shared font + alignment + fit check."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Label, Select, Static, Switch

from ...config import Row
from ...fit import art_width, fits
from ...fit import auto_fit_font as _auto_fit
from ..fonts import SAFE_FONTS, font_options, safe_font_options

ALIGNMENTS = ["left", "center", "right"]


class StepTextFont(Vertical):
    """Edits the row texts, shared banner.font/align, with a live fit check."""

    title = "Step 1 · text + font + alignment"

    def compose(self) -> ComposeResult:
        m = self.app.model
        rows = m.banner.rows
        yield Label("banner text", classes="section-label")
        yield Input(rows[0].text, placeholder="Welcome", id="text")
        yield Label("second row  (optional · leave blank for one line)", classes="section-label")
        yield Input(rows[1].text if len(rows) > 1 else "", placeholder="(none)", id="text2")
        yield Label("font  (safe set · won't break)", classes="section-label")
        yield Select(
            self._font_opts(m.banner.font), id="font", value=m.banner.font, allow_blank=False
        )
        with Vertical(classes="info-row"):
            yield Switch(value=False, id="show-all-fonts")
            yield Label("show all fonts", classes="info-label")
        yield Static("", id="fit-indicator")
        yield Button("auto-fit font", id="autofit", compact=True)
        yield Label("alignment  (position on screen)", classes="section-label")
        yield Select(
            [(a, a) for a in ALIGNMENTS], id="align", value=m.banner.align, allow_blank=False
        )

    def _show_all(self) -> bool:
        try:
            return self.query_one("#show-all-fonts", Switch).value
        except Exception:
            return False

    def _font_opts(self, current: str) -> list[tuple[str, str]]:
        opts = font_options() if self._show_all() else safe_font_options()
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
        self._update_fit()

    def _update_fit(self) -> None:
        m = self.app.model
        target = m.banner.fit_width
        w = art_width(m)
        if target <= 0:
            text = f"[dim]width {w} · fit check off[/dim]"
        elif fits(m):
            text = f"[green]width {w} / {target} ✓[/green]"
        else:
            text = f"[yellow]width {w} / {target} ⚠ (try auto-fit)[/yellow]"
        self.query_one("#fit-indicator", Static).update(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        rows = self.app.model.banner.rows
        if event.input.id == "text":
            rows[0].text = event.value or "Welcome"
        elif event.input.id == "text2":
            self._set_second_row(event.value)
        self._update_fit()
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
            self._update_fit()
            self.app.refresh_preview()
        elif event.select.id == "align":
            self.app.model.banner.align = str(event.value)
            self.app.refresh_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "show-all-fonts":
            font_select = self.query_one("#font", Select)
            current = self.app.model.banner.font
            font_select.set_options(self._font_opts(current))
            font_select.value = current

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "autofit":
            chosen = _auto_fit(self.app.model, list(SAFE_FONTS))
            self.app.model.banner.font = chosen
            font_select = self.query_one("#font", Select)
            font_select.set_options(self._font_opts(chosen))
            font_select.value = chosen
            self._update_fit()
            self.app.refresh_preview()
