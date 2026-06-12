"""Theme gallery — keyboard-driven grid of live template previews."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from ...render import render_art
from ...themes import Theme, all_themes

COLUMNS = 2


class ThemeCard(Static):
    """A focusable card showing a mini preview of one template."""

    can_focus = True

    DEFAULT_CSS = """
    ThemeCard {
        border: round $panel;
        padding: 1 2;
        height: auto;
        min-height: 7;
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
        out = Text()
        out.append(self.theme.name, style=f"bold {self.theme.swatch}")
        out.append(f"   {self.theme.blurb}\n\n", style="dim")
        out.append_text(art)
        return out


class ThemeGallery(Screen):
    """Browse and pick a template. enter = use, c = customize, / = search."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("slash", "search", "Search"),
        ("enter", "use", "Use"),
        ("c", "customize", "Customize"),
        ("up", "move(-2)", ""),
        ("down", "move(2)", ""),
        ("left", "move(-1)", ""),
        ("right", "move(1)", ""),
        ("k", "move(-2)", ""),
        ("j", "move(2)", ""),
        ("h", "move(-1)", ""),
        ("l", "move(1)", ""),
    ]

    CSS = """
    ThemeGallery #gallery { grid-size: 2; grid-gutter: 1 2; height: auto; padding: 1 2; }
    ThemeGallery #search { margin: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static("~/welchost ❯ pick a template", classes="section-label")
        yield Input(placeholder="/ to search…", id="search")
        with VerticalScroll():
            with Grid(id="gallery"):
                for theme in all_themes():
                    yield ThemeCard(theme)
        yield Static(
            "↑↓←→/hjkl move · enter use · c customize · / search · esc back", classes="hint"
        )
        yield Footer()

    def on_mount(self) -> None:
        cards = self._cards()
        if cards:
            cards[0].focus()

    # -- helpers --------------------------------------------------------------

    def _cards(self) -> list[ThemeCard]:
        return [c for c in self.query(ThemeCard) if c.display]

    def _focused_theme(self) -> Theme | None:
        node = self.app.focused
        return node.theme if isinstance(node, ThemeCard) else None

    def _apply(self, theme: Theme) -> None:
        text = self.app.model.banner.text or "Welcome"
        self.app.model = theme.to_config(text=text)

    # -- navigation -----------------------------------------------------------

    def action_move(self, delta: int) -> None:
        cards = self._cards()
        if not cards:
            return
        node = self.app.focused
        idx = cards.index(node) if node in cards else 0
        new = max(0, min(idx + delta, len(cards) - 1))
        cards[new].focus()

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_back(self) -> None:
        if isinstance(self.app.focused, Input):
            cards = self._cards()
            if cards:
                cards[0].focus()
            return
        self.app.pop_screen()

    def on_input_changed(self, event: Input.Changed) -> None:
        q = (event.value or "").strip().lower()
        for card in self.query(ThemeCard):
            card.display = q in card.theme.name.lower() or q in card.theme.blurb.lower()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cards = self._cards()
        if cards:
            cards[0].focus()

    # -- selection ------------------------------------------------------------

    def action_use(self) -> None:
        theme = self._focused_theme()
        if theme is None:
            return
        self._apply(theme)
        from .wizard import Wizard

        self.app.switch_screen(Wizard(start_step=3))

    def action_customize(self) -> None:
        theme = self._focused_theme()
        if theme is None:
            return
        self._apply(theme)
        from .wizard import Wizard

        self.app.switch_screen(Wizard(start_step=0))
