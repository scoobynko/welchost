"""Wizard step 2 — color mode, presets, hex input (keyboard only)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, RadioButton, RadioSet

SWATCHES = [
    "cyan",
    "magenta",
    "green",
    "yellow",
    "red",
    "white",
    "#d97757",
    "#cba6f7",
    "#89dceb",
]


class StepColor(Vertical):
    """Edits banner.color_mode and the solid/gradient colors."""

    title = "step 2 · color"

    def compose(self) -> ComposeResult:
        yield Label("mode", classes="section-label")
        with RadioSet(id="mode"):
            yield RadioButton("solid", id="mode-solid")
            yield RadioButton("gradient", id="mode-gradient")

        with Vertical(id="solid-box"):
            yield Label("color (name or #rrggbb)", classes="section-label")
            yield Input(placeholder="cyan", id="solid")
            yield Label("presets", classes="section-label")
            with RadioSet(id="swatches"):
                for c in SWATCHES:
                    yield RadioButton(c, id=f"sw-{c.lstrip('#')}")

        with Vertical(id="grad-box"):
            yield Label("gradient start", classes="section-label")
            yield Input(placeholder="#ff6b35", id="grad_start")
            yield Label("gradient end", classes="section-label")
            yield Input(placeholder="#f7c59f", id="grad_end")

    def load_from_model(self) -> None:
        m = self.app.model
        is_grad = m.banner.color_mode == "gradient"
        self.query_one("#mode-gradient" if is_grad else "#mode-solid", RadioButton).value = True
        self.query_one("#solid", Input).value = m.solid.value
        self.query_one("#grad_start", Input).value = m.gradient.start
        self.query_one("#grad_end", Input).value = m.gradient.end
        self._toggle(is_grad)

    def _toggle(self, is_grad: bool) -> None:
        self.query_one("#solid-box").display = not is_grad
        self.query_one("#grad-box").display = is_grad

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "mode":
            is_grad = event.radio_set.pressed_index == 1
            self.app.model.banner.color_mode = "gradient" if is_grad else "solid"
            self._toggle(is_grad)
            self.app.refresh_preview()
        elif event.radio_set.id == "swatches" and event.pressed is not None:
            value = str(event.pressed.label)
            self.query_one("#solid", Input).value = value
            self.app.model.solid.value = value
            self.app.refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        m = self.app.model
        if event.input.id == "solid":
            m.solid.value = event.value or "cyan"
        elif event.input.id == "grad_start":
            m.gradient.start = event.value or "cyan"
        elif event.input.id == "grad_end":
            m.gradient.end = event.value or "magenta"
        self.app.refresh_preview()
