"""Wizard step 3 — border style/color + info toggles."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select, Switch

BORDER_STYLES = ["panel", "box", "double", "rounded", "ascii", "none"]

INFO_FIELDS = [
    ("show_user", "user"),
    ("show_host", "host"),
    ("show_os", "os"),
    ("show_datetime", "date/time"),
    ("show_uptime", "uptime"),
    ("show_shell", "shell"),
    ("show_python", "python"),
    ("show_ip", "ip"),
]


class StepDecoration(Vertical):
    """Edits decoration.* and info.* on app.model."""

    title = "Step 3 · decoration + info"

    def compose(self) -> ComposeResult:
        yield Label("Border style")
        yield Select([(s, s) for s in BORDER_STYLES], id="border", allow_blank=False)
        yield Label("Border color (Rich name or #rrggbb)")
        yield Input(placeholder="magenta", id="border_color")
        yield Label("Info widgets")
        for field, label in INFO_FIELDS:
            with Vertical(classes="info-row"):
                yield Switch(id=f"info-{field}")
                yield Label(label, classes="info-label")

    def load_from_model(self) -> None:
        m = self.app.model
        self.query_one("#border", Select).value = m.decoration.border_style
        self.query_one("#border_color", Input).value = m.decoration.border_color
        for field, _ in INFO_FIELDS:
            self.query_one(f"#info-{field}", Switch).value = getattr(m.info, field)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "border" and event.value is not None:
            self.app.model.decoration.border_style = str(event.value)
            self.app.refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "border_color":
            self.app.model.decoration.border_color = event.value or "magenta"
            self.app.refresh_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id and event.switch.id.startswith("info-"):
            field = event.switch.id[len("info-") :]
            setattr(self.app.model.info, field, event.value)
            self.app.refresh_preview()
