"""The 4-step wizard container with a live preview and progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from ..widgets import BannerPreview
from .step_color import StepColor
from .step_confirm import StepConfirm
from .step_decoration import StepDecoration
from .step_text_font import StepTextFont


class Wizard(Screen):
    """Hosts the four steps, swapping visibility, with a shared live preview."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("left", "back", "Prev"),
        ("right", "next", "Next"),
    ]

    CSS = """
    #wizard-body { height: auto; max-width: 100; }
    #progress { text-style: bold; padding: 1 1 0 1; }
    #steps > * { display: none; }
    .info-row { layout: horizontal; height: auto; }
    .info-label { padding: 1 0 0 1; }
    #swatches { height: auto; }
    .swatch { min-width: 10; margin: 0 1 0 0; }
    #nav { height: auto; padding: 1 0; }
    #nav Button { margin: 0 1 0 0; }
    """

    def __init__(self, start_step: int = 0) -> None:
        super().__init__()
        self.index = start_step
        self.steps = [StepTextFont(), StepColor(), StepDecoration(), StepConfirm()]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Center():
            with VerticalScroll(id="wizard-body"):
                yield Static(id="progress")
                with VerticalScroll(id="steps"):
                    yield from self.steps
                with Horizontal(id="nav"):
                    yield Button("← Back", id="back")
                    yield Button("Next →", id="next", variant="primary")
                yield Static("Live preview", classes="panel-title")
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
        self.query_one("#progress", Static).update(
            f"  {current.title}    "
            + " ".join("●" if i == self.index else "○" for i in range(len(self.steps)))
        )
        last = self.index == len(self.steps) - 1
        self.query_one("#next", Button).display = not last
        self.query_one("#back", Button).disabled = self.index == 0

    def action_back(self) -> None:
        self._show_step(self.index - 1)

    def action_next(self) -> None:
        if self.index < len(self.steps) - 1:
            self._show_step(self.index + 1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()
        elif event.button.id == "next":
            self.action_next()
