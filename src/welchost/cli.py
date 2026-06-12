"""Welchost CLI — the only entry point.

Commands: config, preview, reset, doctor, version. The root callback handles the
global ``--dev`` flag. The TUI is imported lazily so non-TUI commands stay fast
and the core never hard-depends on Textual.
"""

from __future__ import annotations

import typer
from rich.console import Console

from . import __version__, detect
from .config import load_config
from .generator import build_figlet, resolve_color
from .generator import reset as do_reset

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
        from .config import WelchostConfig

        cfg = WelchostConfig.default()
    _render_to_console(cfg)


def _render_to_console(cfg) -> None:
    """Render a banner using Rich (mirrors the generated welcome_banner.py)."""
    from rich.align import Align
    from rich.box import ASCII, DOUBLE, HEAVY, ROUNDED, SQUARE
    from rich.panel import Panel
    from rich.text import Text

    art = build_figlet(cfg)
    lines = art.splitlines()

    block = Text()
    for idx, line in enumerate(lines):
        if cfg.banner.color_mode == "gradient":
            block.append_text(_gradient_line(line, cfg.gradient.start, cfg.gradient.end))
        else:
            r, g, b = resolve_color(cfg.solid.value)
            block.append(line, style=f"bold rgb({r},{g},{b})")
        if idx != len(lines) - 1:
            block.append("\n")

    renderable: object = block
    info = _info_text(cfg)
    if info:
        block.append("\n\n")
        block.append_text(info)

    style = cfg.decoration.border_style
    if style == "none":
        console.print(block)
        return
    box_map = {
        "panel": HEAVY,
        "box": SQUARE,
        "double": DOUBLE,
        "rounded": ROUNDED,
        "ascii": ASCII,
    }
    br, bg, bb = resolve_color(cfg.decoration.border_color)
    console.print(
        Panel(
            Align.left(renderable),
            box=box_map.get(style, SQUARE),
            border_style=f"rgb({br},{bg},{bb})",
            expand=False,
            padding=(0, 1),
        )
    )


def _gradient_line(line: str, start: str, end: str):
    from rich.text import Text

    s = resolve_color(start)
    e = resolve_color(end)
    n = max(len(line) - 1, 1)
    t = Text()
    for i, ch in enumerate(line):
        f = i / n
        r = round(s[0] + (e[0] - s[0]) * f)
        g = round(s[1] + (e[1] - s[1]) * f)
        b = round(s[2] + (e[2] - s[2]) * f)
        t.append(ch, style=f"bold rgb({r},{g},{b})")
    return t


def _info_text(cfg):
    import getpass
    import os
    import platform
    import socket
    from datetime import datetime

    from rich.text import Text

    rows = []
    i = cfg.info
    if i.show_user:
        rows.append(("user", getpass.getuser()))
    if i.show_host:
        rows.append(("host", socket.gethostname()))
    if i.show_os:
        mac = platform.mac_ver()[0]
        rows.append(("os", f"macOS {mac}" if mac else platform.system()))
    if i.show_datetime:
        rows.append(("date", datetime.now().strftime("%a %d %b %Y · %H:%M")))
    if i.show_shell:
        rows.append(("shell", os.environ.get("SHELL", "?")))
    if i.show_python:
        rows.append(("python", platform.python_version()))
    if not rows:
        return None
    t = Text()
    for idx, (k, v) in enumerate(rows):
        t.append(f"{k}: ", style="dim")
        t.append(str(v))
        if idx != len(rows) - 1:
            t.append("\n")
    return t


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


@app.command()
def doctor() -> None:
    """Check Ghostty install, environment, and the install chain."""
    from rich.table import Table

    table = Table(title="welchost doctor", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    def row(name, ok, detail=""):
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(name, mark, detail)

    if detect.is_dev():
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
    injected = zshrc.exists() and "# >>> welchost >>>" in zshrc.read_text()
    row(".zshrc sentinel present", injected, str(zshrc))

    console.print(table)


@app.command()
def version() -> None:
    """Print the welchost version."""
    console.print(f"welchost {__version__}")


if __name__ == "__main__":
    app()
