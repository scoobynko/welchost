"""Shared TUI widgets."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Select, Static

from ..config import WelchostConfig
from ..render import render_banner
from ..themes import ACCENT


def apply_visibility(container: Widget, rules: dict[str, bool]) -> None:
    """Show/hide a container's child widgets by id from a {widget_id: visible} map.

    Centralizes the "reveal field X only when control Y has value Z" pattern the
    wizard steps share, so each step declares *what* should be visible and this
    helper owns the `.display` toggling — call it from both ``load_from_model``
    and the relevant change handler to keep the view in sync with the model.
    """
    for widget_id, visible in rules.items():
        container.query_one(f"#{widget_id}").display = visible


# Reusable palette for the color dropdown — the ANSI names plus the brand accent
# and a curated set of *named* hexes. Each entry is (display name, value); the
# value is always a valid Rich color (an ANSI name or a #rrggbb hex) so it can be
# stored verbatim in welchost.toml, while the name is what the user reads.
PRESET_COLORS: list[tuple[str, str]] = [
    ("red", "red"),
    ("green", "green"),
    ("yellow", "yellow"),
    ("blue", "blue"),
    ("magenta", "magenta"),
    ("cyan", "cyan"),
    ("white", "white"),
    ("bright red", "bright_red"),
    ("bright green", "bright_green"),
    ("bright yellow", "bright_yellow"),
    ("bright blue", "bright_blue"),
    ("bright magenta", "bright_magenta"),
    ("bright cyan", "bright_cyan"),
    ("gray", "#808080"),
    ("terracotta", ACCENT),
    ("rose", "#f38ba8"),
    ("peach", "#fab387"),
    ("mint", "#a6e3a1"),
    ("azure", "#89b4fa"),
    ("lavender", "#cba6f7"),
    ("sky", "#89dceb"),
]

# Values only, for fast membership checks ("is this a known preset?").
_PRESET_VALUES = [value for _, value in PRESET_COLORS]

_SWATCH = "■"
_CUSTOM = "\x00custom"  # sentinel value for the "custom hex" option


def _color_label(name: str, value: str) -> Text:
    """A colored square, the friendly name, and (for named hexes) the dim hex."""
    label = f"[{value}]{_SWATCH}[/]  {name}"
    if name != value:  # show the underlying hex for aliases like "peach"
        label += f"  [dim]{value}[/]"
    return Text.from_markup(label)


class ColorField(Vertical):
    """Reusable color picker: a dropdown of preset colors (each with a colored
    square) plus a "custom hex…" entry at the top that reveals an inline input.

    Encapsulates its own widgets and emits a single :class:`ColorField.Changed`
    message (carrying the field instance, so a parent with several of these can
    tell which one changed). Internal Select/Input events are stopped so they
    never leak to the parent.
    """

    DEFAULT_CSS = """
    ColorField { height: auto; margin: 0 0 1 0; }
    ColorField Select { width: 48; }
    ColorField #hex { width: 48; margin: 1 0 0 0; }
    ColorField #hex.hidden { display: none; }
    """

    class Changed(Message):
        """Posted when the chosen color changes."""

        def __init__(self, field: ColorField, value: str) -> None:
            self.field = field
            self.value = value
            super().__init__()

    def __init__(self, label: str, value: str = "", *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._label = label
        self._value = value

    def _options(self) -> list[tuple[Text | str, str]]:
        rows: list[tuple[Text | str, str]] = [(Text.from_markup("[dim]✎  custom hex…[/]"), _CUSTOM)]
        rows.extend((_color_label(name, value), value) for name, value in PRESET_COLORS)
        return rows

    def compose(self) -> ComposeResult:
        is_preset = self._value in _PRESET_VALUES
        yield Label(self._label, classes="section-label")
        yield Select(
            self._options(),
            id="picker",
            value=self._value if is_preset else _CUSTOM,
            allow_blank=False,
        )
        hex_input = Input(self._value, placeholder="name or #rrggbb", id="hex")
        if is_preset:
            hex_input.add_class("hidden")
        yield hex_input

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        """Set the field's value programmatically and sync the controls."""
        self._value = value
        picker = self.query_one("#picker", Select)
        hex_input = self.query_one("#hex", Input)
        hex_input.value = value
        if value in _PRESET_VALUES:
            picker.value = value
            hex_input.add_class("hidden")
        else:
            picker.value = _CUSTOM
            hex_input.remove_class("hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        if event.value is None:
            return
        hex_input = self.query_one("#hex", Input)
        if event.value == _CUSTOM:
            hex_input.remove_class("hidden")
            hex_input.focus()
            self._value = hex_input.value
        else:
            hex_input.add_class("hidden")
            self._value = str(event.value)
            hex_input.value = str(event.value)  # keep in sync; its Changed is stopped below
        self.post_message(self.Changed(self, self._value))

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        # In custom mode the input is the source of truth; otherwise ignore the
        # programmatic sync done by a preset selection.
        if self.query_one("#picker", Select).value == _CUSTOM:
            self._value = event.value
            self.post_message(self.Changed(self, event.value))


class BannerPreview(Static):
    """Live banner preview. Re-renders instantly when `show()` is called."""

    DEFAULT_CSS = """
    BannerPreview {
        border: round $panel;
        padding: 0 1;
        height: auto;
        min-height: 6;
        overflow-x: auto;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cfg: WelchostConfig | None = None

    def show(self, cfg: WelchostConfig) -> None:
        self._cfg = cfg
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        if self._cfg is None:
            return Text("")
        try:
            return render_banner(self._cfg)
        except Exception as exc:  # never crash the UI on a bad font/color
            return Text(f"preview error: {exc}", style="red")
