# Changelog

All notable changes to this project are documented here. This file is
maintained automatically by python-semantic-release from conventional commits;
the v0.1.0 entry below was written by hand for the initial release.

## v0.1.0 (2026-06-12)

### Features

- **core**: Ghostty-aware path/detection layer, `WelchostConfig` with lossless
  TOML round-trip, 12 built-in themes, pyfiglet generator producing a
  self-contained `welcome_banner.py`, idempotent `.zshrc` sentinel injection with
  backups, and a Typer CLI (`config`, `preview`, `reset`, `doctor`, `version`)
  with a global `--dev` sandbox flag.
- **tui**: Textual app with a theme gallery (12 live previews), a 4-step custom
  wizard (text/font over 571 fonts, solid/gradient color, decoration + info
  toggles, confirm & install), and a shared live banner preview.
- **dev**: fully sandboxed DEV mode (`--dev` / `WELCHOST_DEV=1`) writing only to
  `./dev-home/`, with watchdog hot reload.

### Tooling

- pytest suite (63 tests), ruff lint/format, conventional-commit enforcement,
  and CI / release / PR-check / homebrew-test GitHub Actions workflows.
