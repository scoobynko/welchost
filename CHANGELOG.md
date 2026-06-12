# CHANGELOG


## v0.1.0 (2026-06-12)

### Bug Fixes

- **ci**: Run release on ubuntu (semantic-release needs a Linux runner)
  ([`144618e`](https://github.com/scoobynko/welchost/commit/144618e2e8287d01162c2fcdb926530607b5144e))

python-semantic-release is a Docker container action and fails with "Container action is only
  supported on Linux" on macos-latest. The release job is platform-agnostic; the macOS brew check
  stays in homebrew-test.yml.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Chores

- Init project structure
  ([`1bc53f8`](https://github.com/scoobynko/welchost/commit/1bc53f83b662b3bb90cee8ffac9215922c37adfe))

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Continuous Integration

- Skip Homebrew bump until the tap token is configured
  ([`a7c101c`](https://github.com/scoobynko/welchost/commit/a7c101c8e433c78d20234d515d2528d1854f1dd1))

Gate the formula-bump step on HOMEBREW_TAP_TOKEN so a PyPI-only release stays green; the step lights
  up automatically once the tap secret exists.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Documentation

- Add CHANGELOG for v0.1.0
  ([`4b2c7a4`](https://github.com/scoobynko/welchost/commit/4b2c7a4dc539d07a36136da3573e077f16c1c20b))

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- Add CLAUDE.md project specification
  ([`cdaf441`](https://github.com/scoobynko/welchost/commit/cdaf441fe467bab0dad0c880f47f0fb55c41d2f4))

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- Add first-time publishing & release-setup runbook
  ([`c6e0dde`](https://github.com/scoobynko/welchost/commit/c6e0dded4cefc49f969336e51d2a479135529a44))

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- Update spec for alignment, gradients, ornaments, and shell-chain guards
  ([`4ea99f9`](https://github.com/scoobynko/welchost/commit/4ea99f9a921d6244706d000f8376f26102042612))

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Features

- **core**: Banner alignment, directional gradients, ornaments + hardening
  ([`403d85c`](https://github.com/scoobynko/welchost/commit/403d85c30c77f36d62a160b1ac28405dc1380580))

Replace banner.size with banner.align (left/center/right) and add per-block directional gradients
  (horizontal/vertical/diagonal) and predefined flanking ASCII ornaments (new ornaments.py).
  render.py and the generated welcome_banner.py share identical block-gradient/flank/align logic so
  the preview stays WYSIWYG.

Security & robustness for public distribution: - clamp
  align/color_mode/gradient.direction/border_style to their schema enums before baking into the
  generated script (closes code-injection via a hand-edited/shared welchost.toml) - resolve_color
  always returns a 3-tuple, falling back to gray on partial or malformed hex (no more unpack crash
  in the live preview) - generated welcome.zsh only runs when python3 is present; the .zshrc line
  also guards on the shim being readable, so a missing interpreter or shim can never spam errors on
  every shell - load_config tolerates a corrupt welchost.toml (returns None) instead of crashing the
  TUI/CLI on launch - memoize pyfiglet rendering; route the sentinel marker through one constant

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- **core**: Detect, config, themes, generator, cli + templates
  ([`fba2455`](https://github.com/scoobynko/welchost/commit/fba24553f2fbb47d983d6640718f16800942d4d8))

- detect.py: DEV-aware path resolution + Ghostty detection - config.py: WelchostConfig dataclass,
  lossless TOML round-trip - themes.py: 12 built-in themes - generator.py: pyfiglet render,
  self-contained banner script, idempotent .zshrc sentinel + backup, reset - cli.py: Typer app
  (config/preview/reset/doctor/version) with --dev callback - templates: welcome.zsh.j2,
  welcome_banner.py.j2 (pure-Python ANSI)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- **tui**: Keyboard-only redesign — color picker, modals, logo, fixes
  ([`1c127f5`](https://github.com/scoobynko/welchost/commit/1c127f5ee9590ad77b0b7fa69b722bdaf815a030))

- ColorField widget: preset swatches + custom-hex dropdown, reused across the color and decoration
  steps - ConfirmModal: keyboard-driven yes/no overlay; delete and create-new flows route through
  one shared _Menu.confirm helper - unify reset/delete behind one confirm_reset (consistent wording,
  removed paths surfaced); retire the divergent full-screen ResetScreen - centralize config
  lifecycle on the app (adopt_config/clear_config/ new_draft) so the menu always reflects whether a
  config exists - levitating logo: gentle 2-axis idle hover; wordmark render cached - wizard: sticky
  nav (back left / next-save far right), step content height:auto so tall steps (e.g. gradient
  direction) scroll fully, and each step resets to the top on switch - hide the border-color field
  when border style is "none"; shared apply_visibility helper for conditional fields

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- **tui**: Pixel logo, list-based template picker, no emoji
  ([`c39abed`](https://github.com/scoobynko/welchost/commit/c39abedee99ce49c2f1f19685246e4181f3d7886))

- logo: pixel-art ghost + double_blocky wordmark (clear W, pixel edges) - replace all emojis with
  accent block glyphs - template picker: vertical list + live preview (smaller, easy ↑/↓ nav) and
  enter opens the wizard at step 1 so text/font stay editable - docs: update keyboard-nav section

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- **tui**: Redesign — 6 templates, logo, keyboard-only nav, fix save
  ([`1ebdbf2`](https://github.com/scoobynko/welchost/commit/1ebdbf29eae9bf83152c99ae6fe3161bacae19f7))

- themes: 12 -> 6 curated (claude/codex filled, ghost, matrix, sunset, mono), terracotta accent;
  fixes invalid pyfiglet font names - generator: build_figlet falls back to standard on missing
  font; write files atomically (render both before writing) so a bad font can't half-install - tui:
  first-screen logo (pagga wordmark + ghost + prompt), more padding, minimalist; keyboard-only —
  gallery arrows/hjkl, wizard ctrl+arrows + ctrl+s, color presets/mode as RadioSets (no click-only
  buttons) - tests updated for 6 templates + font fallback/validity

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- **tui**: Textual app, theme gallery, 4-step wizard, live preview
  ([`d43047b`](https://github.com/scoobynko/welchost/commit/d43047b3a193b95b82bdc99df239f8027c1fd000))

- render.py: shared Rich banner rendering (CLI + TUI WYSIWYG); cli refactored to use it - app.py:
  WelchostApp holding a live WelchostConfig model; refresh_preview - main_menu: MainMenu/EditMenu +
  Doctor/Preview/Reset screens - theme_gallery: 3-col grid of 12 live theme previews, search,
  enter/c - wizard: 4-step container with progress + shared live BannerPreview - steps:
  text+font(571 searchable), color(solid/gradient+swatches), decoration+info toggles,
  confirm+install - dev_watcher: watchdog hot reload (DEV only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Testing

- Cli, config, generator, detect, dev-mode, themes suites
  ([`faabe76`](https://github.com/scoobynko/welchost/commit/faabe768faf4c608dec0f9ea6eef278be5d1b86d))

63 tests: sentinel idempotency, DEV sandbox isolation, lossless config round-trip, all 12 theme
  fonts valid, self-contained banner script.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

- Cover alignment, gradient direction, ornaments, and config tolerance
  ([`de802ab`](https://github.com/scoobynko/welchost/commit/de802ab373352f9a05d656a12a7ca48afab88c25))

Round-trip + defaults for align/direction/ornament, theme ornament-name validation (mirrors the font
  check), gradient-direction baking, and that a legacy/removed key loads without crashing.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
