"""Wizard step 4 — confirm: file diff summary + install status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ... import detect


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
        has = zshrc.exists() and "# >>> welchost >>>" in zshrc.read_text()
        zstate = "[dim]already injected[/dim]" if has else "[green]inject sentinel[/green]"
        lines.append(f"  {zstate}  {zshrc.name}")
        return "\n".join(lines)

    def do_save(self) -> None:
        from ...config import save_config
        from ...generator import install

        try:
            save_config(self.app.model)
            paths = install(self.app.model)
            msg = "[green]✓ installed[/green] — open a new Ghostty window to see it\n"
            msg += "\n".join(f"  • {v}" for v in paths.values())
            msg += "\n\n[dim]press q to quit[/dim]"
        except Exception as exc:
            msg = f"[red]✗ install failed:[/red] {exc}"
        self.query_one("#save-status", Static).update(msg)
