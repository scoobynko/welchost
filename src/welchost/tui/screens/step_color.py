"""Wizard step 2 — color mode + reusable color pickers (keyboard only)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, RadioButton, RadioSet, Select

from ..widgets import ColorField, apply_visibility

DIRECTIONS = ["horizontal", "vertical", "diagonal"]


class StepColor(Vertical):
    """Edits banner.color_mode and the solid/gradient colors via ColorField."""

    title = "step 2 · color"

    def compose(self) -> ComposeResult:
        m = self.app.model
        yield Label("mode", classes="section-label")
        with RadioSet(id="mode"):
            yield RadioButton("solid", id="mode-solid")
            yield RadioButton("gradient", id="mode-gradient")

        with Vertical(id="solid-box"):
            yield ColorField("color", m.solid.value, id="solid")

        with Vertical(id="grad-box"):
            yield ColorField("gradient start", m.gradient.start, id="grad_start")
            yield ColorField("gradient end", m.gradient.end, id="grad_end")
            yield Label("direction", classes="section-label")
            yield Select(
                [(d, d) for d in DIRECTIONS],
                id="grad_dir",
                value=m.gradient.direction,
                allow_blank=False,
            )

    def load_from_model(self) -> None:
        m = self.app.model
        is_grad = m.banner.color_mode == "gradient"
        self.query_one("#mode-gradient" if is_grad else "#mode-solid", RadioButton).value = True
        self.query_one("#solid", ColorField).set_value(m.solid.value)
        self.query_one("#grad_start", ColorField).set_value(m.gradient.start)
        self.query_one("#grad_end", ColorField).set_value(m.gradient.end)
        self.query_one("#grad_dir", Select).value = m.gradient.direction
        self._toggle(is_grad)

    def _toggle(self, is_grad: bool) -> None:
        apply_visibility(self, {"solid-box": not is_grad, "grad-box": is_grad})

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        # ColorField stops its own swatch RadioSet events, so only "mode" arrives.
        if event.radio_set.id == "mode":
            is_grad = event.radio_set.pressed_index == 1
            self.app.model.banner.color_mode = "gradient" if is_grad else "solid"
            self._toggle(is_grad)
            self.app.refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "grad_dir" and event.value is not None:
            self.app.model.gradient.direction = str(event.value)
            self.app.refresh_preview()

    def on_color_field_changed(self, event: ColorField.Changed) -> None:
        m = self.app.model
        if event.field.id == "solid":
            m.solid.value = event.value or "cyan"
        elif event.field.id == "grad_start":
            m.gradient.start = event.value or "cyan"
        elif event.field.id == "grad_end":
            m.gradient.end = event.value or "magenta"
        self.app.refresh_preview()
