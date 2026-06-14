"""Main menu (no config) and edit menu (config exists)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Label, ListItem, ListView, Static

from ... import detect
from ...generator import SENTINEL_START
from ...themes import ACCENT
from ..logo import Logo


class _Menu(Screen):
    """Base list-driven menu screen. Fully keyboard-driven."""

    BINDINGS = [Binding("escape", "back", "Back")]

    CSS = """
    _Menu #menu, _Menu #menu > ListItem { background: transparent; }
    _Menu #menu:focus > ListItem.-highlighted { background: $boost; }
    /* Vertical containers + ListView default to height: 1fr, which splits the
       viewport and squeezes the auto-height header (logo/byline) to nothing on
       short terminals. Size them to content so the header keeps full height and
       the VerticalScroll only scrolls when content truly overflows. */
    _Menu #menu-box, _Menu #edit-header, _Menu #menu { height: auto; }
    """

    def action_back(self) -> None:
        """Pop to the previous screen. Root menus (MainMenu/EditMenu) override
        this to a no-op so esc on the home screen can't pop the last screen off
        the stack and leave a blank (black) screen."""
        self.app.pop_screen()

    def items(self) -> list[tuple[str, str]]:  # (id, label)
        raise NotImplementedError

    def header_widget(self) -> Widget:
        return Logo()

    def compose(self) -> ComposeResult:
        # VerticalScroll so a short terminal scrolls instead of squeezing the
        # auto-height header (logo + byline) down to nothing — the bug where the
        # "by scooby" credit vanished on small windows.
        with VerticalScroll():
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

    def confirm(self, message: str, *, yes_label: str, on_yes) -> None:
        """Push a yes/no ConfirmModal and run ``on_yes`` only if confirmed."""
        from .modals import ConfirmModal

        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                on_yes()

        self.app.push_screen(
            ConfirmModal(message, yes_label=yes_label, no_label="cancel"),
            on_result,
        )

    def confirm_reset(self, *, verb: str, done_label: str) -> None:
        """Confirm, then remove all welchost files, clear in-memory state, and
        return to the main menu. Shared by MainMenu's reset and EditMenu's delete
        so both use the same modal, wording, and post-action behavior. ``verb`` is
        the imperative used in the prompt/button ("Delete"); ``done_label`` is the
        past-tense word used in the result toast ("Deleted")."""
        from ...generator import reset as do_reset

        def on_yes() -> None:
            removed = do_reset()
            self.app.clear_config()
            if removed:
                names = ", ".join(p.name for p in removed)
                self.app.notify(f"{done_label} - removed {names}.", timeout=6)
            else:
                self.app.notify("Nothing to remove.", timeout=6)
            self.app.switch_screen(MainMenu())

        self.confirm(
            f"{verb} your [bold]welcome screen[/bold]?\n"
            f"[dim]Removes {_reset_target()}. This cannot be undone.[/dim]",
            yes_label=verb.lower(),
            on_yes=on_yes,
        )


def _reset_target() -> str:
    """One source of truth for the reset/delete scope wording."""
    return (
        "the dev-home sandbox" if detect.is_dev() else "all welchost files and the ~/.zshrc block"
    )


class MainMenu(_Menu):
    """Shown when there is no existing config."""

    # Home screen: esc must do nothing (there's no screen to go back to).
    BINDINGS = [Binding("escape", "back", show=False)]

    def action_back(self) -> None:
        pass

    def items(self) -> list[tuple[str, str]]:
        a = f"[{ACCENT}]"
        rows = [
            ("themes", f"{a}▦[/]  browse templates   [dim]fast[/dim]"),
            ("custom", f"{a}◧[/]  build custom screen [dim]full control[/dim]"),
        ]
        # doctor is a dev-only diagnostic — hidden from normal users.
        if detect.is_dev():
            rows.append(("doctor", f"{a}◈[/]  doctor [dim]dev[/dim]"))
        rows.append(("reset", f"{a}▩[/]  reset"))
        return rows

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
            self.confirm_reset(verb="Reset", done_label="Reset")


class EditMenu(_Menu):
    """Top-level menu shown when a config already exists.

    Branded like the main menu (logo) with an explicit indication that a welcome
    screen is active, then a clean choice: edit current vs create a new one.
    """

    # Home screen: esc must do nothing (there's no screen to go back to).
    BINDINGS = [Binding("escape", "back", show=False)]

    def action_back(self) -> None:
        pass

    def header_widget(self) -> Widget:
        m = self.app.model
        color = "gradient" if m.banner.color_mode == "gradient" else m.solid.value
        summary = f"{m.banner.text} · {m.banner.font} · {color}"
        return Vertical(
            Logo(),
            Static(f"[{ACCENT}]●[/] welcome screen active", classes="section-label"),
            Static(f"[dim]{summary}[/dim]", classes="hint"),
            id="edit-header",
        )

    def items(self) -> list[tuple[str, str]]:
        a = f"[{ACCENT}]"
        rows = [
            ("edit", f"{a}▸[/]  edit current"),
            ("new", f"{a}▸[/]  create new  [dim](replaces current)[/dim]"),
            ("preview", f"{a}▸[/]  preview current"),
        ]
        # doctor is a dev-only diagnostic — hidden from normal users.
        if detect.is_dev():
            rows.append(("doctor", f"{a}▸[/]  doctor [dim]dev[/dim]"))
        rows.append(("delete", f"{a}▸[/]  delete welcome screen"))
        return rows

    def handle(self, key: str) -> None:
        if key == "edit":
            self.app.push_screen(EditCurrentMenu())
        elif key == "new":
            self._confirm_create_new()
        elif key == "preview":
            self.app.push_screen(PreviewScreen())
        elif key == "doctor":
            self.app.push_screen(DoctorScreen())
        elif key == "delete":
            self.confirm_reset(verb="Delete", done_label="Deleted")

    def _confirm_create_new(self) -> None:
        def on_yes() -> None:
            # New build: only the editor resets; the installed files stay until a
            # save, so had_config is deliberately left untouched (app.new_draft).
            self.app.new_draft()
            self.app.switch_screen(MainMenu())

        self.confirm(
            "Start a [bold]new welcome screen[/bold]?\n"
            "[dim]This discards your current settings. Installed files and "
            "~/.zshrc only change when you save.[/dim]",
            yes_label="create new",
            on_yes=on_yes,
        )


class EditCurrentMenu(_Menu):
    """Granular edit options for the existing welcome screen."""

    def header_widget(self) -> Widget:
        return Static("~/welchost ❯ edit current", classes="section-label")

    def items(self) -> list[tuple[str, str]]:
        a = f"[{ACCENT}]"
        return [
            ("text", f"{a}▤[/]  text & font"),
            ("color", f"{a}▦[/]  color"),
            ("deco", f"{a}◧[/]  decoration & info"),
            ("theme", f"{a}▩[/]  load a template (replace all)"),
            ("rewizard", f"{a}◇[/]  full re-wizard"),
            ("preview", f"{a}▣[/]  preview current"),
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
            lines.append("[yellow]DEV mode[/yellow] - sandboxed at ./dev-home/\n")
        lines.append(f"{mark(detect.ghostty_installed())} Ghostty installed")
        lines.append(f"{mark(detect.is_ghostty_terminal())} TERM_PROGRAM=ghostty")
        lines.append(f"{mark(detect.get_config_path().exists())} welchost.toml exists")
        lines.append(f"{mark(detect.get_welcome_zsh_path().exists())} welcome.zsh exists")
        lines.append(f"{mark(detect.get_welcome_banner_path().exists())} welcome_banner.py exists")
        zshrc = detect.get_zshrc()
        injected = zshrc.exists() and SENTINEL_START in zshrc.read_text()
        lines.append(f"{mark(injected)} .zshrc sentinel present")
        return "\n".join(lines)
