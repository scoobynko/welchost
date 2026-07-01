"""Wizard step 4 — confirm: file diff summary + install status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ... import detect
from ...generator import SENTINEL_START


class StepConfirm(Vertical):
    """Shows what will be written; installs via the wizard's save action."""

    title = "step 4 · confirm"

    def compose(self) -> ComposeResult:
        yield Static(self._summary(), id="diff-summary")
        yield Static("press ctrl+s or the save button to install", id="save-status", classes="hint")

    def load_from_model(self) -> None:
        self.query_one("#diff-summary", Static).update(self._summary())

    def _summary(self) -> str:
        lines = ["[bold]files welchost will write[/bold]\n"]
        for label, path in [
            ("config", detect.get_config_path()),
            ("welcome.zsh", detect.get_welcome_zsh_path()),
            ("welcome_banner.py", detect.get_welcome_banner_path()),
        ]:
            state = "[yellow]update[/yellow]" if path.exists() else "[green]create[/green]"
            lines.append(f"  {state}  {label}")
        zshrc = detect.get_zshrc()
        has = zshrc.exists() and SENTINEL_START in zshrc.read_text()
        zstate = "[dim]already injected[/dim]" if has else "[green]inject sentinel[/green]"
        lines.append(f"  {zstate}  {zshrc.name}")
        return "\n".join(lines)

    def _apply_autofit(self) -> None:
        """Width-safety, under the hood: if the banner would overflow its
        ``banner.fit_width``, silently swap to the largest safe font that fits.

        Runs only on the wizard save path, so a font set by hand in welchost.toml
        (the TOML escape hatch) is never touched. No-op when the banner fits or the
        fit target is disabled (``fit_width <= 0``)."""
        from ...fit import auto_fit_font, fits
        from ..fonts import SAFE_FONTS

        model = self.app.model
        if not fits(model):
            model.banner.font = auto_fit_font(model, list(SAFE_FONTS))

    def do_save(self) -> None:
        from ...config import save_config
        from ...generator import install

        self._apply_autofit()
        try:
            save_config(self.app.model)
            paths = install(self.app.model)
        except Exception as exc:
            self.query_one("#save-status", Static).update(f"[red]✗ install failed:[/red] {exc}")
            return
        # Success: a config now exists — record it and return to the edit menu.
        self.app.adopt_config(self.app.model)
        names = ", ".join(p.name for p in paths.values())
        self.app.notify(f"Installed {names} - open a new Ghostty window to see it.", timeout=6)
        self._go_home()

    def _go_home(self) -> None:
        from .main_menu import EditMenu

        app = self.app
        # Pop everything above the default base screen, then push a fresh edit
        # menu (config now exists). Pushing onto the base is the normal pattern;
        # switch_screen-ing the base screen mounts incorrectly.
        while len(app.screen_stack) > 1:
            app.pop_screen()
        app.push_screen(EditMenu())
