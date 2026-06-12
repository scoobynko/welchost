"""The 4-step wizard container with a live preview and progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from ..widgets import BannerPreview
from .step_color import StepColor
from .step_confirm import StepConfirm
from .step_decoration import StepDecoration
from .step_text_font import StepTextFont


class Wizard(Screen):
    """Hosts the four steps, swapping visibility, with a shared live preview."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("ctrl+right", "next", "Next step"),
        ("ctrl+left", "prev", "Prev step"),
        ("ctrl+s", "save", "Save & install"),
    ]

    CSS = """
    Wizard #wizard-body { width: 76; max-width: 100%; padding: 1 2; }
    Wizard #progress { text-style: bold; padding: 0 0 1 0; }
    Wizard #steps > * { display: none; }
    Wizard .info-row { layout: horizontal; height: auto; padding: 0 0; }
    Wizard .info-label { padding: 1 0 0 1; }
    Wizard Input, Wizard Select, Wizard RadioSet { margin: 0 0 1 0; }
    Wizard #font_list { height: 8; border: round $panel; }
    Wizard #nav { height: auto; padding: 1 0; align-horizontal: left; }
    Wizard #nav Button { margin: 0 2 0 0; }
    Wizard BannerPreview { margin: 1 0 0 0; }
    """

    def __init__(self, start_step: int = 0) -> None:
        super().__init__()
        self.index = start_step
        self.steps = [StepTextFont(), StepColor(), StepDecoration(), StepConfirm()]

    def compose(self) -> ComposeResult:
        with Center():
            with VerticalScroll(id="wizard-body"):
                yield Static(id="progress")
                with VerticalScroll(id="steps"):
                    yield from self.steps
                with Horizontal(id="nav"):
                    yield Button("← back", id="back", compact=True)
                    yield Button("next →", id="next", variant="primary", compact=True)
                    yield Button("save & install", id="save", variant="success", compact=True)
                yield Static("live preview", classes="panel-title")
                yield BannerPreview()
        yield Footer()

    def on_mount(self) -> None:
        self._show_step(self.index)
        self.app.refresh_preview()

    def _show_step(self, index: int) -> None:
        self.index = max(0, min(index, len(self.steps) - 1))
        for i, step in enumerate(self.steps):
            step.display = i == self.index
        current = self.steps[self.index]
        if hasattr(current, "load_from_model"):
            current.load_from_model()
        dots = " ".join("●" if i == self.index else "○" for i in range(len(self.steps)))
        self.query_one("#progress", Static).update(f"{current.title}    {dots}")
        last = self.index == len(self.steps) - 1
        self.query_one("#next", Button).display = not last
        self.query_one("#save", Button).display = last
        self.query_one("#back", Button).disabled = self.index == 0
        self._focus_first(current)

    def _focus_first(self, step) -> None:
        for widget in step.query("*"):
            if getattr(widget, "focusable", False):
                widget.focus()
                return

    def action_prev(self) -> None:
        self._show_step(self.index - 1)

    def action_next(self) -> None:
        if self.index < len(self.steps) - 1:
            self._show_step(self.index + 1)

    def action_save(self) -> None:
        self._show_step(len(self.steps) - 1)
        self.steps[3].do_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_prev()
        elif event.button.id == "next":
            self.action_next()
        elif event.button.id == "save":
            self.action_save()
