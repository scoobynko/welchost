"""Wizard step 3 — border style/color + info toggles."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select, Switch

from ...config import VALID_INFO_LAYOUTS
from ...ornaments import VALID_ORNAMENTS
from ..widgets import ColorField, apply_visibility

BORDER_STYLES = ["panel", "box", "double", "rounded", "ascii", "none"]

# Only the two everyday widgets are exposed in the wizard; the rest remain in the
# schema for TOML power users.
INFO_FIELDS = [
    ("show_user", "user"),
    ("show_datetime", "date/time"),
]


class StepDecoration(Vertical):
    """Edits decoration.* and info.* on app.model."""

    title = "Step 3 · decoration + info"

    def compose(self) -> ComposeResult:
        # Construct widgets with the model's current values so the allow_blank
        # Select and the Switches never fire a mount-default Changed that
        # clobbers the model (e.g. a saved border_style/info toggle).
        m = self.app.model
        yield Label("border style", classes="section-label")
        yield Select(
            [(s, s) for s in BORDER_STYLES],
            id="border",
            value=m.decoration.border_style,
            allow_blank=False,
        )
        yield ColorField("border color", m.decoration.border_color, id="border_color")
        yield Label("ornament  (flanks the banner)", classes="section-label")
        yield Select(
            [(o, o) for o in VALID_ORNAMENTS],
            id="ornament",
            value=m.ornament.name,
            allow_blank=False,
        )
        yield Label("info widgets", classes="section-label")
        for field, label in INFO_FIELDS:
            with Vertical(classes="info-row"):
                yield Switch(value=getattr(m.info, field), id=f"info-{field}")
                yield Label(label, classes="info-label")
        yield Label("metadata layout  (inline row · or stacked lines)", classes="section-label")
        yield Select(
            [(layout, layout) for layout in VALID_INFO_LAYOUTS],
            id="info-layout",
            value=m.info.layout,
            allow_blank=False,
        )
        yield Label("metadata separator  (glyph between inline items)", classes="section-label")
        yield Input(m.info.separator, placeholder="·", id="info-separator")
        yield Label("metadata accent  (auto = match banner · or a color)", classes="section-label")
        yield Input(m.info.accent, placeholder="auto or #rrggbb", id="info-accent")

    def on_mount(self) -> None:
        self._sync_border_color()

    def load_from_model(self) -> None:
        m = self.app.model
        self.query_one("#border", Select).value = m.decoration.border_style
        self.query_one("#border_color", ColorField).set_value(m.decoration.border_color)
        self.query_one("#ornament", Select).value = m.ornament.name
        for field, _ in INFO_FIELDS:
            self.query_one(f"#info-{field}", Switch).value = getattr(m.info, field)
        self.query_one("#info-layout", Select).value = m.info.layout
        self.query_one("#info-separator", Input).value = m.info.separator
        self.query_one("#info-accent", Input).value = m.info.accent
        self._sync_border_color()

    def _sync_border_color(self) -> None:
        # A border color is meaningless without a border, so only show the field
        # when a border style other than "none" is selected.
        show = self.app.model.decoration.border_style != "none"
        apply_visibility(self, {"border_color": show})

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is None:
            return
        if event.select.id == "border":
            self.app.model.decoration.border_style = str(event.value)
            self._sync_border_color()
            self.app.refresh_preview()
        elif event.select.id == "ornament":
            self.app.model.ornament.name = str(event.value)
            self.app.refresh_preview()
        elif event.select.id == "info-layout":
            self.app.model.info.layout = str(event.value)
            self.app.refresh_preview()

    def on_color_field_changed(self, event: ColorField.Changed) -> None:
        if event.field.id == "border_color":
            self.app.model.decoration.border_color = event.value or "magenta"
            self.app.refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "info-separator":
            self.app.model.info.separator = event.value or "·"
            self.app.refresh_preview()
        elif event.input.id == "info-accent":
            self.app.model.info.accent = event.value or "auto"
            self.app.refresh_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id and event.switch.id.startswith("info-"):
            field = event.switch.id[len("info-") :]
            setattr(self.app.model.info, field, event.value)
            self.app.refresh_preview()
