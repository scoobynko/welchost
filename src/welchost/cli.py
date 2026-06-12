"""Welchost CLI — the only entry point.

Commands: config, preview, reset, doctor, version. The root callback handles the
global ``--dev`` flag. The TUI is imported lazily so non-TUI commands stay fast
and the core never hard-depends on Textual.
"""

from __future__ import annotations

import typer
from rich.console import Console

from . import __version__, detect
from .config import WelchostConfig, load_config
from .generator import SENTINEL_START
from .generator import reset as do_reset
from .render import render_banner

app = typer.Typer(
    name="welchost",
    help="Create and manage a Ghostty terminal welcome screen.",
    no_args_is_help=False,
    add_completion=True,
)
console = Console()


def _enable_dev() -> None:
    detect.DEV_MODE = True
    detect.ensure_config_dir()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    dev: bool = typer.Option(
        False, "--dev", help="Run sandboxed against ./dev-home/ (never touches ~)."
    ),
) -> None:
    """Welchost — a welcome screen for Ghostty."""
    if dev or detect.is_dev():
        _enable_dev()
    # Bare `welchost` (no subcommand) launches the TUI, same as `config`.
    if ctx.invoked_subcommand is None:
        _launch_tui()


def _launch_tui() -> None:
    """Lazy-import and run the Textual app."""
    try:
        from .tui.app import run as run_tui
    except Exception as exc:  # pragma: no cover - import guard
        console.print(f"[red]TUI unavailable:[/red] {exc}")
        raise typer.Exit(1) from exc
    run_tui()


@app.command()
def config() -> None:
    """Launch the interactive TUI (create wizard or edit menu)."""
    _launch_tui()


@app.command()
def preview() -> None:
    """Render the current banner to stdout (no TUI, no file changes)."""
    cfg = load_config()
    if cfg is None:
        console.print(
            "[yellow]No config found.[/yellow] Showing the default banner. "
            "Run [bold]welchost config[/bold] to create one."
        )
        cfg = WelchostConfig.default()
    console.print(render_banner(cfg))


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Remove all welchost files and the .zshrc injection."""
    target = "the dev-home sandbox" if detect.is_dev() else "your welchost files and .zshrc block"
    if not yes:
        confirmed = typer.confirm(f"This will remove {target}. Continue?")
        if not confirmed:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)
    removed = do_reset()
    if removed:
        console.print("[green]Removed:[/green]")
        for p in removed:
            console.print(f"  • {p}")
    else:
        console.print("[dim]Nothing to remove.[/dim]")


@app.command(hidden=True)
def doctor() -> None:
    """[dev only] Diagnostics: Ghostty install, env, and the install chain.

    Hidden from the user-facing CLI and refuses to run outside dev mode
    (``--dev`` or ``WELCHOST_DEV=1``). It's a debugging aid, not a user command.
    """
    if not detect.is_dev():
        console.print(
            "[red]welchost doctor[/red] is a development-only diagnostic. "
            "Re-run with [bold]--dev[/bold] or set [bold]WELCHOST_DEV=1[/bold]."
        )
        raise typer.Exit(2)

    from rich.table import Table

    table = Table(title="welchost doctor", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    def row(name, ok, detail=""):
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(name, mark, detail)

    console.print("[yellow]DEV mode[/yellow] — sandboxed at ./dev-home/")

    row(
        "Ghostty installed",
        detect.ghostty_installed(),
        "skipped in dev" if detect.is_dev() else "/Applications/Ghostty.app or `ghostty`",
    )
    in_ghostty = detect.is_ghostty_terminal()
    row("TERM_PROGRAM=ghostty", in_ghostty, detect.term_program() or "unset")

    cfg_path = detect.get_config_path()
    row("welchost.toml exists", cfg_path.exists(), str(cfg_path))
    row(
        "welcome.zsh exists",
        detect.get_welcome_zsh_path().exists(),
        str(detect.get_welcome_zsh_path()),
    )
    row(
        "welcome_banner.py exists",
        detect.get_welcome_banner_path().exists(),
        str(detect.get_welcome_banner_path()),
    )

    zshrc = detect.get_zshrc()
    injected = zshrc.exists() and SENTINEL_START in zshrc.read_text()
    row(".zshrc sentinel present", injected, str(zshrc))

    console.print(table)


@app.command()
def version() -> None:
    """Print the welchost version."""
    console.print(f"welchost {__version__}")


if __name__ == "__main__":
    app()
