"""Main menu (no config) and edit menu (config exists)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Label, ListItem, ListView, Static

from ... import detect
from ...themes import ACCENT
from ..logo import Logo


class _Menu(Screen):
    """Base list-driven menu screen. Fully keyboard-driven."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def items(self) -> list[tuple[str, str]]:  # (id, label)
        raise NotImplementedError

    def header_widget(self) -> Widget:
        return Logo()

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="menu-box"):
                yield self.header_widget()
                yield ListView(
                    *[ListItem(Label(label), id=key) for key, label in self.items()],
                    id="menu",
                )
                yield Static("↑/↓ move · enter select · q quit", classes="hint")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#menu", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.handle(event.item.id or "")

    def handle(self, key: str) -> None:
        raise NotImplementedError


class MainMenu(_Menu):
    """Shown when there is no existing config."""

    def items(self) -> list[tuple[str, str]]:
        a = f"[{ACCENT}]"
        return [
            ("themes", f"{a}▦[/]  browse templates   [dim]fast[/dim]"),
            ("custom", f"{a}◧[/]  build custom screen [dim]full control[/dim]"),
            ("doctor", f"{a}◈[/]  doctor"),
            ("reset", f"{a}▩[/]  reset"),
        ]

    def handle(self, key: str) -> None:
        if key == "themes":
            from .theme_gallery import ThemeGallery

            self.app.push_screen(ThemeGallery())
        elif key == "custom":
            from .wizard import Wizard

            self.app.push_screen(Wizard(start_step=0))
        elif key == "doctor":
            self.app.push_screen(DoctorScreen())
        elif key == "reset":
            self.app.push_screen(ResetScreen())


class EditMenu(_Menu):
    """Shown when a config already exists."""

    def header_widget(self) -> Widget:
        return Static("~/welchost ❯ edit", classes="section-label")

    def items(self) -> list[tuple[str, str]]:
        a = f"[{ACCENT}]"
        return [
            ("text", f"{a}▤[/]  text & font"),
            ("color", f"{a}▦[/]  color"),
            ("deco", f"{a}◧[/]  decoration & info"),
            ("theme", f"{a}▩[/]  load a template (replace all)"),
            ("rewizard", f"{a}◇[/]  full re-wizard"),
            ("preview", f"{a}▣[/]  preview current"),
            ("doctor", f"{a}◈[/]  doctor"),
            ("reset", f"{a}▚[/]  reset"),
        ]

    def handle(self, key: str) -> None:
        from .wizard import Wizard

        if key == "text":
            self.app.push_screen(Wizard(start_step=0))
        elif key == "color":
            self.app.push_screen(Wizard(start_step=1))
        elif key == "deco":
            self.app.push_screen(Wizard(start_step=2))
        elif key == "rewizard":
            self.app.push_screen(Wizard(start_step=0))
        elif key == "theme":
            from .theme_gallery import ThemeGallery

            self.app.push_screen(ThemeGallery())
        elif key == "preview":
            self.app.push_screen(PreviewScreen())
        elif key == "doctor":
            self.app.push_screen(DoctorScreen())
        elif key == "reset":
            self.app.push_screen(ResetScreen())


class PreviewScreen(Screen):
    """Full-screen preview of the current model."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        from ..widgets import BannerPreview

        yield Static("~/welchost ❯ preview", classes="section-label")
        with Center():
            yield BannerPreview()
        yield Footer()

    def on_mount(self) -> None:
        self.app.refresh_preview()


class DoctorScreen(Screen):
    """Render the doctor checks."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        with Center():
            yield Static(self._report(), id="doctor-report")
        yield Footer()

    def _report(self) -> str:
        def mark(ok: bool) -> str:
            return "[green]✓[/green]" if ok else "[red]✗[/red]"

        lines = ["[bold]welchost doctor[/bold]\n"]
        if detect.is_dev():
            lines.append("[yellow]DEV mode[/yellow] — sandboxed at ./dev-home/\n")
        lines.append(f"{mark(detect.ghostty_installed())} Ghostty installed")
        lines.append(f"{mark(detect.is_ghostty_terminal())} TERM_PROGRAM=ghostty")
        lines.append(f"{mark(detect.get_config_path().exists())} welchost.toml exists")
        lines.append(f"{mark(detect.get_welcome_zsh_path().exists())} welcome.zsh exists")
        lines.append(f"{mark(detect.get_welcome_banner_path().exists())} welcome_banner.py exists")
        zshrc = detect.get_zshrc()
        injected = zshrc.exists() and "# >>> welchost >>>" in zshrc.read_text()
        lines.append(f"{mark(injected)} .zshrc sentinel present")
        return "\n".join(lines)


class ResetScreen(Screen):
    """Confirm and perform a reset."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("y", "do_reset", "Confirm reset"),
        ("n", "app.pop_screen", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        target = (
            "the dev-home sandbox" if detect.is_dev() else "all welchost files and the .zshrc block"
        )
        with Center():
            yield Static(
                f"This will remove [bold]{target}[/bold].\n\n"
                "Press [bold]y[/bold] to confirm, [bold]n[/bold]/esc to cancel.",
                id="reset-confirm",
            )
        yield Footer()

    def action_do_reset(self) -> None:
        from ...generator import reset as do_reset

        removed = do_reset()
        msg = (
            "Removed:\n" + "\n".join(f"  • {p}" for p in removed)
            if removed
            else "Nothing to remove."
        )
        self.query_one("#reset-confirm", Static).update(msg)
