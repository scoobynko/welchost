"""Theme gallery — 3-column grid of live theme previews."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from ...render import render_art
from ...themes import Theme, all_themes


class ThemeCard(Static):
    """A focusable card showing a mini preview of one theme."""

    can_focus = True

    DEFAULT_CSS = """
    ThemeCard {
        border: round $panel;
        padding: 0 1;
        height: auto;
        min-height: 6;
    }
    ThemeCard:focus { border: round $accent; background: $boost; }
    """

    def __init__(self, theme: Theme) -> None:
        super().__init__(id=f"theme-{theme.name}")
        self.theme = theme

    def render(self) -> Text:
        cfg = self.theme.to_config(text="Abc")
        cfg.decoration.border_style = "none"
        try:
            art = render_art(cfg)
        except Exception:
            art = Text("(font error)")
        out = Text(f"{self.theme.name}\n", style="bold")
        out.append_text(art)
        return out


class ThemeGallery(Screen):
    """Browse and pick a theme. enter = use, c = customize, / = search."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("slash", "search", "Search"),
        ("enter", "use", "Use"),
        ("c", "customize", "Customize"),
    ]

    CSS = """
    #gallery { grid-size: 3; grid-gutter: 1; height: auto; padding: 1; }
    #search { margin: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Input(placeholder="/ to search themes…", id="search")
        with VerticalScroll():
            with Grid(id="gallery"):
                for theme in all_themes():
                    yield ThemeCard(theme)
        yield Static("enter use · c customize · / search · esc back", classes="hint")
        yield Footer()

    def on_mount(self) -> None:
        first = self.query(ThemeCard).first()
        if first:
            first.focus()

    # -- search ---------------------------------------------------------------

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        q = (event.value or "").strip().lower()
        for card in self.query(ThemeCard):
            card.display = q in card.theme.name.lower()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        for card in self.query(ThemeCard):
            if card.display:
                card.focus()
                break

    # -- selection ------------------------------------------------------------

    def _focused_theme(self) -> Theme | None:
        node = self.app.focused
        return node.theme if isinstance(node, ThemeCard) else None

    def _apply(self, theme: Theme) -> None:
        text = self.app.model.banner.text or "Welcome"
        self.app.model = theme.to_config(text=text)

    def action_use(self) -> None:
        theme = self._focused_theme()
        if theme is None:
            return
        self._apply(theme)
        from .wizard import Wizard

        self.app.switch_screen(Wizard(start_step=3))  # straight to confirm

    def action_customize(self) -> None:
        theme = self._focused_theme()
        if theme is None:
            return
        self._apply(theme)
        from .wizard import Wizard

        self.app.switch_screen(Wizard(start_step=0))
