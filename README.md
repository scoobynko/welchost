# 💀 Welchost

> **welc**ome + g**host** — a macOS CLI that creates and manages a welcome screen for the [Ghostty](https://ghostty.org) terminal.

Welchost generates a banner that greets you every time you open Ghostty: big
[pyfiglet](https://github.com/pwaller/pyfiglet) ASCII art, solid colors or
gradients, an optional border and flanking ornaments, and system info (user,
host, OS, uptime, …).

```
Ghostty launches
  → ~/.zshrc sources ~/.config/ghostty/welcome.zsh
    → welcome.zsh runs python3 ~/.config/ghostty/welcome_banner.py
      → banner renders in your terminal
```

---

# For users

## Install

```bash
# Homebrew (macOS)
brew install scoobynko/welchost/welchost

# or pipx / PyPI
pipx install welchost
```

## Usage

```bash
welchost            # launch the interactive TUI (themes + custom wizard)
welchost config     # same as above
welchost preview    # render the current banner to stdout
welchost reset      # remove all welchost files and the .zshrc injection
welchost version    # print version
```

Run `welchost`, pick a template or build your own in the wizard, save, then open
a new Ghostty window to see it. Re-run `welchost` any time to edit.

## What it manages

Welchost owns three files in `~/.config/ghostty/`:

- `welchost.toml` — your config, the single source of truth
- `welcome.zsh` — thin shell shim (generated)
- `welcome_banner.py` — the renderer (generated)

It **never** touches Ghostty's own `config` file, and it injects exactly one
guarded line into `~/.zshrc` between sentinel markers (backed up before any
edit). The banner only runs in an interactive Ghostty shell.

## Privacy

Welchost can send an **anonymous, opt-in** launch ping so we can see roughly how
many people use it. **Nothing is sent unless you say yes** to a one-time prompt
on first run. It then carries a random UUID and coarse facts only — welchost
version, install method, OS name/version, CPU arch, and Python minor version.
**No usernames, paths, IP addresses, config contents, or machine fingerprints**,
the UUID is never tied to a real-person profile, and data is stored in the EU.

If you opted in and change your mind, the ping is skipped when either is set:

```bash
export WELCHOST_NO_TELEMETRY=1   # welchost-specific opt-out
export DO_NOT_TRACK=1            # the cross-tool standard (consoledonottrack.com)
```

The anonymous id and your choice live in `~/.config/ghostty/analytics.json` and
are removed by `welchost reset`. Telemetry is also off entirely in `--dev` mode.

## Uninstall

```bash
welchost reset      # removes the generated files and the ~/.zshrc block
pipx uninstall welchost   # or: brew uninstall welchost
```

---

# For contributors

Contributions welcome. The project is macOS-only (Ghostty + zsh) and targets
Python 3.11+.

## Setup

```bash
git clone https://github.com/scoobynko/welchost
cd welchost
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install        # ruff + conventional-commit hooks
```

## Develop safely with `--dev`

Add `--dev` (or set `WELCHOST_DEV=1`) to run **fully sandboxed** against
`./dev-home/` — it never touches your real `~/.config/ghostty/` or `~/.zshrc`,
skips the Ghostty check, and enables hot-reload of the TUI.

```bash
welchost --dev            # sandboxed TUI
welchost --dev reset      # wipes ./dev-home/ only
welchost --dev doctor     # diagnostics: Ghostty, env, and install-chain health
```

`doctor` is a **development-only** diagnostic: it's hidden from the user-facing
CLI and refuses to run outside `--dev` / `WELCHOST_DEV=1`.

## Test & lint

```bash
pytest                    # full suite
ruff check src tests      # lint
ruff format src tests     # format
```

## Architecture

Strict one-way dependency: **`tui → core`**, never the reverse.

```
src/welchost/
├── detect.py      # where files go + Ghostty/env detection + DEV mode
├── config.py      # WelchostConfig dataclass ↔ welchost.toml
├── themes.py      # built-in templates (plain data)
├── ornaments.py   # flanking ASCII ornaments (plain data)
├── generator.py   # render templates + manage the ~/.zshrc sentinel
├── render.py      # banner rendering (shared by preview + generated script)
├── cli.py         # Typer entry point
├── tui/           # Textual UI (depends on core)
└── templates/     # welcome.zsh.j2, welcome_banner.py.j2
```

The full specification lives in [CLAUDE.md](./CLAUDE.md) — read it before making
non-trivial changes.

## Contributing workflow

- `main` is protected: changes land via **pull request** with passing CI
  (lint + tests on Python 3.11/3.12/3.13). No direct pushes or force-pushes.
- **Conventional commits** are required (enforced by commitlint / pre-commit):
  `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `perf:`, `ci:`.
- Keep the core Textual-free; never hardcode paths (use `detect`); all user
  output goes through a Rich `Console`.

## Releases (automated — don't bump versions by hand)

On merge to `main`, [python-semantic-release](https://python-semantic-release.readthedocs.io)
reads the conventional commits, bumps the version (`feat:` → minor, `fix:` →
patch, `feat!:`/`BREAKING CHANGE:` → major), tags it, publishes to **PyPI**, and
updates the **Homebrew** formula.

## License

MIT © Welchost Contributors
