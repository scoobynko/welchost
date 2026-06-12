"""Wizard step 2 — color mode, swatches, hex input."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

SWATCHES = [
    "cyan",
    "magenta",
    "green",
    "yellow",
    "red",
    "blue",
    "white",
    "#cba6f7",
    "#89dceb",
    "#fe8019",
]


class StepColor(Vertical):
    """Edits banner.color_mode and the solid/gradient colors."""

    title = "Step 2 · color"

    def compose(self) -> ComposeResult:
        yield Label("Color mode")
        with RadioSet(id="mode"):
            yield RadioButton("Solid", id="mode-solid")
            yield RadioButton("Gradient", id="mode-gradient")

        with Vertical(id="solid-box"):
            yield Label("Solid color (Rich name or #rrggbb)")
            yield Input(placeholder="cyan", id="solid")
            with Horizontal(id="swatches"):
                for c in SWATCHES:
                    yield Button(c, id=f"sw-{c.lstrip('#')}", classes="swatch")

        with Vertical(id="grad-box"):
            yield Label("Gradient start")
            yield Input(placeholder="#ff6b35", id="grad_start")
            yield Label("Gradient end")
            yield Input(placeholder="#f7c59f", id="grad_end")

    def load_from_model(self) -> None:
        m = self.app.model
        is_grad = m.banner.color_mode == "gradient"
        target = "#mode-gradient" if is_grad else "#mode-solid"
        self.query_one(target, RadioButton).value = True
        self.query_one("#solid", Input).value = m.solid.value
        self.query_one("#grad_start", Input).value = m.gradient.start
        self.query_one("#grad_end", Input).value = m.gradient.end
        self._toggle(is_grad)

    def _toggle(self, is_grad: bool) -> None:
        self.query_one("#solid-box").display = not is_grad
        self.query_one("#grad-box").display = is_grad

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        is_grad = event.radio_set.pressed_index == 1
        self.app.model.banner.color_mode = "gradient" if is_grad else "solid"
        self._toggle(is_grad)
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("sw-"):
            value = str(event.button.label)
            self.query_one("#solid", Input).value = value
            self.app.model.solid.value = value
            self.app.refresh_preview()
