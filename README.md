# 💀 Welchost

> **welc**ome + g**host** — a macOS CLI that creates and manages a welcome screen for the [Ghostty](https://ghostty.org) terminal.

Welchost generates a banner that greets you every time you open Ghostty: big
[pyfiglet](https://github.com/pwaller/pyfiglet) ASCII art, colors or gradients,
a border, and optional system info (user, host, OS, uptime, …).

```
Ghostty launches
  → ~/.zshrc sources ~/.config/ghostty/welcome.zsh
    → welcome.zsh runs python3 ~/.config/ghostty/welcome_banner.py
      → banner renders in your terminal
```

## Install

```bash
# Homebrew (macOS)
brew install scoobynko/welchost/welchost

# pipx / PyPI
pipx install welchost
```

## Usage

```bash
welchost            # launch the interactive TUI (themes + custom wizard)
welchost config     # same as above
welchost preview    # render the current banner to stdout
welchost doctor     # check Ghostty, env, and the install chain
welchost reset      # remove all welchost files and the .zshrc injection
welchost version    # print version
```

Add `--dev` (or `WELCHOST_DEV=1`) to run fully sandboxed against `./dev-home/`
without touching your real config or `~/.zshrc`.

## What it manages

Welchost owns three files in `~/.config/ghostty/`:

- `welchost.toml` — config, the single source of truth
- `welcome.zsh` — thin shell shim (generated)
- `welcome_banner.py` — the renderer (generated)

It **never** touches Ghostty's own `config` file, and it injects exactly one
guarded line into `~/.zshrc` between sentinel markers.

See [CLAUDE.md](./CLAUDE.md) for the full specification.

## License

MIT © Welchost Contributors
