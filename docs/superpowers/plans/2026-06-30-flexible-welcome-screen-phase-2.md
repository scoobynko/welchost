# Flexible Welcome Screen — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make banners hard to break (a curated "won't-break" font set + an in-wizard width check with one-click auto-fit) and make the system-info metadata read as part of the banner (a styled inline row that inherits the banner's palette).

**Architecture:** Builds on Phase 1's rows model. Three threads: (1) a `SAFE_FONTS` subset surfaced by default in the wizard font picker with a "show all" escape hatch; (2) a new core `fit.py` that measures rendered art width and picks the largest safe font that fits `banner.fit_width`; (3) styled metadata — new `[info]` fields (`layout`/`separator`/`accent`) drive an inline, palette-inheriting info row rendered identically in `render.py` and the generated `welcome_banner.py`.

**Tech Stack:** Python 3.11+, dataclasses, TOML, pyfiglet, Rich, Textual, Jinja2, pytest.

## Global Constraints

- **Min Python 3.11**; macOS-only.
- **WYSIWYG parity:** any render change lands in BOTH `src/welchost/render.py` AND `src/welchost/templates/welcome_banner.py.j2`; coloring math stays identical. The existing `tests/test_parity.py` guards this (it currently runs with info OFF; Task 5 adds an info-ON parity case using only host/run-stable fields).
- **Generated `welcome_banner.py` has NO third-party imports** (no rich/pyfiglet/jinja2) — pure-Python ANSI only; guarded by `test_generated_banner_is_self_contained`.
- **Lossless TOML round-trip**; new `[info]` fields must round-trip and default sensibly so existing configs keep working.
- **Core stays Textual-free:** `config.py`, `render.py`, `generator.py`, `fit.py`, `ornaments.py`, `detect.py` must never `import` from `welchost.tui`. (This is why `fit.auto_fit_font` takes the candidate font list as a parameter — the TUI passes `SAFE_FONTS` in; core never imports the font catalog from `tui/`.)
- **All paths via `detect`**; all output via Rich `Console`; always `mkdir -p` the config dir before writing.
- Conventional commits; line length 100; ruff clean (`.venv/bin/ruff check src tests`, `.venv/bin/ruff format --check src tests`).
- **Test/lint via the venv** (no `python`/`pytest`/`ruff` on PATH): `.venv/bin/python -m pytest`, `.venv/bin/ruff`.
- Suite is GREEN at branch HEAD (124 passing).

## Deferred from Phase 2 (explicit YAGNI)

- **Separator-boundary wrapping** of an over-wide inline info row (spec §4) is NOT implemented here — metadata is rendered as a single inline line. Default metadata (`user · date`, ~40 cols) is well under `fit_width`. If multi-field metadata commonly overflows in practice, add wrapping as a follow-up. This keeps both renderers and parity simple.
- **Runtime compact fallback** is Phase 3, untouched here.

---

## File Structure (Phase 2)

| File | Responsibility | Change |
|------|----------------|--------|
| `src/welchost/tui/fonts.py` | Font catalog for the picker | Add `SAFE_FONTS` + `safe_font_options()` |
| `tests/test_fonts.py` (new) | Font-catalog guards | SAFE_FONTS ⊆ CURATED, all render cleanly |
| `src/welchost/fit.py` (new) | Width measurement + auto-fit (core) | `art_width`, `fits`, `auto_fit_font` |
| `tests/test_fit.py` (new) | Fit logic | width/fits/auto-fit behavior |
| `src/welchost/config.py` | Schema | `Info.layout/separator/accent` + `VALID_INFO_LAYOUTS` |
| `tests/test_config.py` | Config | round-trip of new `[info]` fields |
| `src/welchost/render.py` | Rich preview | inline styled `info_text` (+ stacked legacy) |
| `tests/test_render.py` | Render | inline info styling assertions |
| `src/welchost/generator.py` | Generated source | bake info styling (`_info_style`) |
| `src/welchost/templates/welcome_banner.py.j2` | Generated renderer | inline styled info + colored-info render() |
| `tests/test_parity.py` | Parity | info-ON parity case (stable fields) |
| `src/welchost/tui/screens/step_text_font.py` | Wizard step 1 | safe-default picker + show-all toggle + fit indicator + auto-fit |
| `src/welchost/tui/screens/step_decoration.py` | Wizard step 3 | metadata layout/separator/accent controls |
| `tests/test_wizard_rows.py` | Wizard | fit/auto-fit + metadata-control tests |

---

## Task 1: SAFE_FONTS catalog + picker helper

**Files:**
- Modify: `src/welchost/tui/fonts.py`
- Test: `tests/test_fonts.py` (create)

**Interfaces:**
- Produces: `SAFE_FONTS: list[str]` (a vetted subset of `CURATED`); `safe_font_options() -> list[tuple[str, str]]` (label/value pairs for the picker, safe fonts only).
- Consumes: existing `CURATED`, `font_options()`, `all_fonts()` in the same module.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fonts.py`:

```python
"""The curated and safe font lists must be valid and render cleanly."""

from __future__ import annotations

import pytest

from welchost.generator import _render_figlet, font_exists
from welchost.tui.fonts import CURATED, SAFE_FONTS, safe_font_options

# Printable characters a banner might use.
_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .-_!?"


def test_safe_fonts_are_a_subset_of_curated():
    assert set(SAFE_FONTS) <= set(CURATED)
    assert SAFE_FONTS, "expected at least one safe font"


@pytest.mark.parametrize("font", SAFE_FONTS)
def test_safe_font_is_valid(font):
    assert font_exists(font)


@pytest.mark.parametrize("font", SAFE_FONTS)
def test_safe_font_renders_charset_cleanly(font):
    art = _render_figlet(font, _CHARSET)
    lines = [ln for ln in art.splitlines() if ln.strip()]
    # Renders to non-empty, multi-line block art with no blank-output character.
    assert lines, f"{font} produced empty art"
    # All visible lines share one height band (no row collapsed to empty mid-block).
    assert len(lines) >= 2


def test_safe_font_options_shape():
    opts = safe_font_options()
    assert opts == [(f, f) for f in SAFE_FONTS]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_fonts.py -q`
Expected: FAIL — `ImportError: cannot import name 'SAFE_FONTS'`.

- [ ] **Step 3: Add `SAFE_FONTS` and `safe_font_options`**

In `src/welchost/tui/fonts.py`, after the `CURATED` list, add:

```python
# A vetted subset of CURATED that renders cleanly and at a predictable width
# across the usual banner charset — the "won't-break" set shown by default in the
# wizard. All are filled/block or clean classic fonts verified by tests/test_fonts.py.
SAFE_FONTS = [
    "ansi_shadow",
    "ansi_regular",
    "block",
    "banner3",
    "colossal",
    "standard",
    "big",
    "doom",
    "slant",
    "straight",
]
```

At the end of the module add:

```python
@lru_cache(maxsize=1)
def safe_font_options() -> list[tuple[str, str]]:
    """(label, value) pairs for the default ("won't-break") font picker."""
    return [(name, name) for name in SAFE_FONTS]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_fonts.py -q`
Expected: PASS (all parametrized cases).

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/tui/fonts.py tests/test_fonts.py
git commit -m "feat(fonts): add curated SAFE_FONTS set and safe_font_options"
```

---

## Task 2: Width measurement + auto-fit (`fit.py`)

**Files:**
- Create: `src/welchost/fit.py`
- Test: `tests/test_fit.py` (create)

**Interfaces:**
- Produces:
  - `art_width(cfg: WelchostConfig, font: str | None = None) -> int` — widest rendered line across all rows (incl. ornament flanking), using `font` if given else `cfg.banner.font`.
  - `fits(cfg: WelchostConfig) -> bool` — `True` if `fit_width <= 0` (disabled) or `art_width(cfg) <= fit_width`.
  - `auto_fit_font(cfg: WelchostConfig, candidates: list[str]) -> str` — largest candidate whose `art_width` ≤ `fit_width`; if none fit, the least-overflowing candidate; with `fit_width <= 0`, the widest candidate. Returns `cfg.banner.font` if `candidates` is empty.
- Consumes: `welchost.generator._render_figlet`, `welchost.ornaments.get_ornament`, `welchost.config.WelchostConfig`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fit.py`:

```python
"""Width measurement and auto-fit font selection."""

from __future__ import annotations

from welchost.config import Row, WelchostConfig
from welchost.fit import art_width, auto_fit_font, fits


def _cfg(text="Hi", font="standard"):
    cfg = WelchostConfig.default()
    cfg.banner.font = font
    cfg.banner.rows = [Row(text=text)]
    return cfg


def test_art_width_positive_and_ornament_adds_width():
    cfg = _cfg("Hi")
    base = art_width(cfg)
    assert base > 0
    cfg.ornament.name = "ghosts"
    assert art_width(cfg) > base


def test_art_width_font_override():
    cfg = _cfg("WELCOME", font="standard")
    narrow = art_width(cfg, font="standard")
    wide = art_width(cfg, font="colossal")
    assert wide > narrow


def test_fits_respects_target():
    cfg = _cfg("Hi")
    cfg.banner.fit_width = 5
    assert fits(cfg) is False
    cfg.banner.fit_width = 1000
    assert fits(cfg) is True
    cfg.banner.fit_width = 0  # disabled
    assert fits(cfg) is True


def test_auto_fit_picks_a_fitting_font_when_one_exists():
    cfg = _cfg("WELCOME", font="colossal")
    cfg.banner.fit_width = 40
    candidates = ["colossal", "big", "standard", "slant"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen in candidates
    # The chosen font actually fits the target.
    assert art_width(cfg, font=chosen) <= 40


def test_auto_fit_returns_widest_when_target_disabled():
    cfg = _cfg("WELCOME")
    cfg.banner.fit_width = 0
    candidates = ["standard", "colossal"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen == "colossal"  # widest


def test_auto_fit_least_overflow_when_none_fit():
    cfg = _cfg("WELCOME")
    cfg.banner.fit_width = 1  # impossibly small
    candidates = ["standard", "colossal"]
    chosen = auto_fit_font(cfg, candidates)
    assert chosen == "standard"  # least overflow
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_fit.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'welchost.fit'`.

- [ ] **Step 3: Implement `fit.py`**

Create `src/welchost/fit.py`:

```python
"""Design-time banner width measurement and auto-fit font selection.

Pure core (no Textual). ``auto_fit_font`` takes its candidate font list as an
argument so this module never imports the font catalog from ``welchost.tui``.
"""

from __future__ import annotations

from .config import WelchostConfig
from .generator import _render_figlet
from .ornaments import get_ornament


def _block_width(font: str, text: str) -> int:
    """Widest line of a single row's figlet block (blank edges stripped)."""
    lines = _render_figlet(font, text).splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(ln) for ln in lines), default=0)


def _ornament_pad(cfg: WelchostConfig) -> int:
    """Extra columns the flanking ornament adds (matches render's 3-space gap)."""
    left, right = get_ornament(cfg.ornament.name)
    pad = 0
    lw = max((len(s) for s in left), default=0)
    rw = max((len(s) for s in right), default=0)
    if lw:
        pad += lw + 3
    if rw:
        pad += rw + 3
    return pad


def art_width(cfg: WelchostConfig, font: str | None = None) -> int:
    """Widest rendered line across all banner rows, including ornament flanking."""
    f = font or cfg.banner.font
    widest = max((_block_width(f, row.text) for row in cfg.banner.rows), default=0)
    return widest + _ornament_pad(cfg)


def fits(cfg: WelchostConfig) -> bool:
    """True if the banner is within its fit target (or the target is disabled)."""
    return cfg.banner.fit_width <= 0 or art_width(cfg) <= cfg.banner.fit_width


def auto_fit_font(cfg: WelchostConfig, candidates: list[str]) -> str:
    """Pick the largest candidate font that fits ``cfg.banner.fit_width``.

    If none fit, return the least-overflowing candidate. With the target
    disabled (``fit_width <= 0``) return the widest candidate. Falls back to the
    current font when ``candidates`` is empty.
    """
    if not candidates:
        return cfg.banner.font
    measured = [(f, art_width(cfg, font=f)) for f in candidates]
    target = cfg.banner.fit_width
    if target > 0:
        fitting = [(f, w) for f, w in measured if w <= target]
        if fitting:
            return max(fitting, key=lambda fw: fw[1])[0]
        return min(measured, key=lambda fw: fw[1])[0]
    return max(measured, key=lambda fw: fw[1])[0]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_fit.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (no regressions).

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/fit.py tests/test_fit.py
git commit -m "feat(fit): art width measurement and auto-fit font selection"
```

---

## Task 3: `[info]` styling fields in the schema

**Files:**
- Modify: `src/welchost/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Info.layout: str = "inline"`, `Info.separator: str = "·"`, `Info.accent: str = "auto"`; module constant `VALID_INFO_LAYOUTS = ("inline", "stacked")`. Round-trips losslessly; defaults applied for older configs.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_info_styling_fields_default(fake_home):
    info = WelchostConfig.default().info
    assert info.layout == "inline"
    assert info.separator == "·"
    assert info.accent == "auto"


def test_info_styling_roundtrip(fake_home):
    cfg = WelchostConfig.default()
    cfg.info.layout = "stacked"
    cfg.info.separator = "|"
    cfg.info.accent = "#ff0000"
    save_config(cfg)
    loaded = load_config()
    assert loaded is not None
    assert loaded.info.layout == "stacked"
    assert loaded.info.separator == "|"
    assert loaded.info.accent == "#ff0000"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_config.py -q -k info_styling`
Expected: FAIL — `AttributeError: 'Info' object has no attribute 'layout'`.

- [ ] **Step 3: Add the fields**

In `src/welchost/config.py`, add the constant near the other `VALID_*` tuples (after `VALID_BORDER_STYLES`):

```python
VALID_INFO_LAYOUTS = ("inline", "stacked")
```

Extend the `Info` dataclass (append the three fields after `show_ip`):

```python
@dataclass
class Info:
    # Default to a clean inline footer; the rest stay available for TOML power
    # users but are off by default and hidden from the wizard.
    show_user: bool = True
    show_datetime: bool = True
    show_host: bool = False
    show_os: bool = False
    show_uptime: bool = False
    show_shell: bool = False
    show_python: bool = False
    show_ip: bool = False
    # Styling (Phase 2): inline row that inherits the banner palette.
    layout: str = "inline"  # inline | stacked
    separator: str = "·"
    accent: str = "auto"  # auto (inherit) | Rich color name / hex
```

`to_toml_dict` already serializes the whole `Info` via `asdict`, and `from_toml_dict` builds it via `_build(Info, ...)` which ignores unknown keys and applies defaults — so older configs without these fields load with the defaults. No (de)serialization change needed.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/config.py tests/test_config.py
git commit -m "feat(config): add info layout/separator/accent styling fields"
```

---

## Task 4: Styled inline metadata in `render.py` (preview)

**Files:**
- Modify: `src/welchost/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Info.layout/separator/accent` (Task 3); `resolve_color`; `cfg.banner.rows[0]`; `cfg.decoration`.
- Produces: `info_text(cfg)` renders an inline styled `Text` when `layout == "inline"` (labels in accent color, values in dimmed banner color, separators in dim accent) and the legacy stacked `dim key: value` when `layout == "stacked"`. Helper `_info_accent_rgb(cfg)`/`_info_value_rgb(cfg)`.

Note (parity): the generated side is updated in Task 5. Between Tasks 4 and 5 the existing `test_parity.py` stays green because it runs with all info flags OFF; an info-ON config's preview will briefly differ from the generated script until Task 5 — a one-task strangler window.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:

```python
def _info_cfg(layout="inline"):
    from welchost.config import Row, SolidColor

    cfg = WelchostConfig.default()
    cfg.banner.rows = [Row(text="Hi", color_mode="solid", solid=SolidColor(value="#3a96dd"))]
    cfg.decoration.border_style = "none"
    cfg.info.show_user = True
    cfg.info.show_datetime = False
    cfg.info.show_host = True
    cfg.info.layout = layout
    cfg.info.separator = "·"
    cfg.info.accent = "#d97757"
    return cfg


def test_info_inline_is_single_line_with_accent_and_separator(fake_home):
    from welchost.render import info_text

    t = info_text(_info_cfg("inline"))
    assert t is not None
    assert "\n" not in t.plain  # single inline line
    assert "·" in t.plain  # separator between the two items
    styles = {str(s.style) for s in t.spans}
    # Accent (terracotta #d97757 -> 217,119,87) used for labels.
    assert any("217,119,87" in s for s in styles)


def test_info_stacked_is_multiline_legacy(fake_home):
    from welchost.render import info_text

    t = info_text(_info_cfg("stacked"))
    assert t is not None
    assert "\n" in t.plain  # one line per item
    assert "user: " in t.plain
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_render.py -q -k info`
Expected: FAIL — the current `info_text` always renders stacked `dim key: value`, so the inline single-line / accent-color assertions fail.

- [ ] **Step 3: Rewrite `info_text` (and add helpers)**

In `src/welchost/render.py`, replace the whole `info_text` function (currently lines ~166–194) with:

```python
def _info_items(cfg: WelchostConfig) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
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
    if i.show_uptime:
        rows.append(("uptime", "…"))
    if i.show_shell:
        rows.append(("shell", os.environ.get("SHELL", "?")))
    if i.show_python:
        rows.append(("python", platform.python_version()))
    if i.show_ip:
        rows.append(("ip", "…"))
    return rows


def _banner_color(cfg: WelchostConfig) -> str:
    first = cfg.banner.rows[0]
    return first.gradient.start if first.color_mode == "gradient" else first.solid.value


def _info_accent_rgb(cfg: WelchostConfig) -> tuple[int, int, int]:
    accent = cfg.info.accent
    if accent != "auto":
        return resolve_color(accent)
    if cfg.decoration.border_style != "none":
        return resolve_color(cfg.decoration.border_color)
    return resolve_color(_banner_color(cfg))


def info_text(cfg: WelchostConfig) -> Text | None:
    items = _info_items(cfg)
    if not items:
        return None

    if cfg.info.layout == "stacked":
        t = Text()
        for idx, (k, v) in enumerate(items):
            t.append(f"{k}: ", style="dim")
            t.append(str(v))
            if idx != len(items) - 1:
                t.append("\n")
        return t

    ar, ag, ab = _info_accent_rgb(cfg)
    vr, vg, vb = resolve_color(_banner_color(cfg))
    label_style = f"rgb({ar},{ag},{ab})"
    value_style = f"dim rgb({vr},{vg},{vb})"
    sep_style = f"dim rgb({ar},{ag},{ab})"
    sep = f"  {cfg.info.separator}  "
    t = Text()
    for idx, (k, v) in enumerate(items):
        if idx:
            t.append(sep, style=sep_style)
        t.append(f"{k} ", style=label_style)
        t.append(str(v), style=value_style)
    return t
```

`render_banner` is unchanged (it still appends `info_text(cfg)` after `"\n\n"`).

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_render.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (the parity test runs info-OFF and is unaffected).

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/render.py tests/test_render.py
git commit -m "feat(render): styled inline metadata row in the preview"
```

---

## Task 5: Styled inline metadata in the generated script (parity)

**Files:**
- Modify: `src/welchost/generator.py`
- Modify: `src/welchost/templates/welcome_banner.py.j2`
- Test: `tests/test_parity.py`, `tests/test_generator.py`

**Interfaces:**
- Consumes: `Info.layout/separator/accent`; `resolve_color`; first-row color.
- Produces: generated `welcome_banner.py` with an `INFO_STYLE` dict (`{layout, separator, accent:[r,g,b], value:[r,g,b]}`) and an `info_lines()` returning `(plain_lines, disp_lines)`; `render()` prints colored info from `disp_lines` while measuring width from `plain_lines`. Output matches `render.py` for the same config.

- [ ] **Step 1: Add the failing parity + generator tests**

Add to `tests/test_parity.py` two configs + ensure the parametrize list includes them. Append factories and extend `_PARITY_CONFIGS`:

```python
def _cfg_inline_info_no_border():
    """Inline styled metadata, border none. Only run-stable info fields (no date)."""
    cfg = _base_cfg()
    cfg.decoration.border_style = "none"
    cfg.ornament.name = "none"
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="#3a96dd")),
    ]
    cfg.info.layout = "inline"
    cfg.info.separator = "·"
    cfg.info.accent = "#d97757"
    cfg.info.show_user = True
    cfg.info.show_host = True
    cfg.info.show_python = True
    cfg.info.show_os = True
    cfg.info.show_shell = True
    # all time/network-dependent fields stay off (set in _base_cfg)
    return cfg


def _cfg_inline_info_box_border():
    cfg = _cfg_inline_info_no_border()
    cfg.decoration.border_style = "box"
    cfg.decoration.border_color = "cyan"
    return cfg
```

Then extend the list:

```python
_PARITY_CONFIGS = [
    pytest.param(_cfg_solid_two_rows_no_border, id="solid-two-rows-no-border"),
    pytest.param(_cfg_gradient_two_rows_no_border, id="gradient-two-rows-no-border"),
    pytest.param(_cfg_solid_two_rows_box_border, id="solid-two-rows-box"),
    pytest.param(_cfg_gradient_one_row_ghosts, id="gradient-one-row-ghosts"),
    pytest.param(_cfg_mixed_two_rows_rounded, id="mixed-two-rows-rounded"),
    pytest.param(_cfg_inline_info_no_border, id="inline-info-no-border"),
    pytest.param(_cfg_inline_info_box_border, id="inline-info-box"),
]
```

> Note for the implementer: the existing parity assertions compare the ANSI-stripped grid and the ordered `38;2;r;g;b` triples. If exact triple ORDER proves brittle for info (Rich vs hand-rolled segmentation), it is acceptable to also assert the multiset/`sorted()` of triples in addition to the grid — but do NOT weaken the grid (visible-text) assertion. Reconcile by matching segmentation, never by skipping the check. If you must change the shared assertion, keep it at least as strong for the art rows.

Add to `tests/test_generator.py`:

```python
def test_info_style_baked(fake_home):
    cfg = WelchostConfig.default()
    cfg.info.layout = "inline"
    cfg.info.accent = "#d97757"
    _, banner = generator.write_generated_files(cfg)
    src = banner.read_text()
    assert "INFO_STYLE" in src
    assert '"layout": "inline"' in src
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_parity.py tests/test_generator.py -q`
Expected: FAIL — the generated info is still plain `k: v` (no styling / no `INFO_STYLE`), so the inline-info parity cases and `test_info_style_baked` fail.

- [ ] **Step 3: Bake the info style in `generator.py`**

In `src/welchost/generator.py`, add `_info_style` next to `_info_dict`:

```python
def _info_style(config: WelchostConfig) -> dict:
    info = config.info
    first = config.banner.rows[0]
    banner_color = first.gradient.start if first.color_mode == "gradient" else first.solid.value
    banner_rgb = resolve_color(banner_color)
    if info.accent != "auto":
        accent_rgb = resolve_color(info.accent)
    elif config.decoration.border_style != "none":
        accent_rgb = resolve_color(config.decoration.border_color)
    else:
        accent_rgb = banner_rgb
    return {
        "layout": _enum(info.layout, VALID_INFO_LAYOUTS, "inline"),
        "separator": info.separator,
        "accent": list(accent_rgb),
        "value": list(banner_rgb),
    }
```

Add the import of `VALID_INFO_LAYOUTS` to the existing `from .config import (...)` block. Then in `render_welcome_banner`, add one kwarg to `template.render(...)`:

```python
        info=repr(_info_dict(config)),
        info_style=json.dumps(_info_style(config)),
```

(`json.dumps` is safe here: all values are `str`/`list[int]`; `separator="·"` serializes as a `·` escape, which is valid Python.)

- [ ] **Step 4: Rewrite the template's info + render()**

In `src/welchost/templates/welcome_banner.py.j2`:

Add the baked style next to `INFO` (after line `INFO = {{ info }}`):

```jinja
INFO = {{ info }}
INFO_STYLE = {{ info_style }}
```

Replace the whole `info_lines()` function with:

```python
def info_lines():
    # Returns (plain_lines, disp_lines). Plain is used for width/border math;
    # disp carries the ANSI styling. Mirrors render.py's info_text.
    items = []
    if INFO.get("show_user"):
        items.append(("user", getpass.getuser()))
    if INFO.get("show_host"):
        items.append(("host", socket.gethostname()))
    if INFO.get("show_os"):
        mac = platform.mac_ver()[0]
        items.append(("os", f"macOS {mac}" if mac else platform.platform(terse=True)))
    if INFO.get("show_datetime"):
        items.append(("date", datetime.now().strftime("%a %d %b %Y · %H:%M")))
    if INFO.get("show_uptime"):
        items.append(("uptime", _uptime()))
    if INFO.get("show_shell"):
        items.append(("shell", os.environ.get("SHELL", "?")))
    if INFO.get("show_python"):
        items.append(("python", platform.python_version()))
    if INFO.get("show_ip"):
        items.append(("ip", _local_ip()))
    if not items:
        return [], []

    if INFO_STYLE["layout"] == "stacked":
        plain = [f"{k}: {v}" for k, v in items]
        disp = [f"\x1b[2m{k}: {RESET}{v}" for k, v in items]
        return plain, disp

    ar, ag, ab = INFO_STYLE["accent"]
    vr, vg, vb = INFO_STYLE["value"]
    sep = INFO_STYLE["separator"]
    label_c = f"\x1b[38;2;{ar};{ag};{ab}m"
    value_c = f"\x1b[2;38;2;{vr};{vg};{vb}m"
    sep_c = f"\x1b[2;38;2;{ar};{ag};{ab}m"
    plain_parts, disp_parts = [], []
    for idx, (k, v) in enumerate(items):
        if idx:
            plain_parts.append(f"  {sep}  ")
            disp_parts.append(f"{sep_c}  {sep}  {RESET}")
        plain_parts.append(f"{k} ")
        disp_parts.append(f"{label_c}{k} {RESET}")
        plain_parts.append(str(v))
        disp_parts.append(f"{value_c}{v}{RESET}")
    return ["".join(plain_parts)], ["".join(disp_parts)]
```

Replace the `render()` function with a version that carries a colored body parallel to the plain body:

```python
def render():
    art_lines, colored = build_rows()
    artw = max((visible_len(ln) for ln in art_lines), default=0)

    if ORN_LEFT or ORN_RIGHT:
        art_lines, colored = flank(art_lines, colored, artw)

    info_plain, info_disp = info_lines()
    body = list(art_lines)
    colored_body = list(colored)
    if info_plain:
        body.append("")
        colored_body.append("")
        body.extend(info_plain)
        colored_body.extend(info_disp)

    width = max((visible_len(ln) for ln in body), default=0)

    if BORDER_STYLE == "none":
        lead = align_pad(width)
        for ln in colored_body:
            print(lead + ln)
        return

    chars = BORDERS.get(BORDER_STYLE, BORDERS["box"])
    tl, h, tr, v, bl, br = chars[0], chars[1], chars[2], chars[3], chars[4], chars[5]
    pad = 1
    inner = width + pad * 2
    bc = fg(BORDER_RGB) if BORDER_RGB else ""
    bce = RESET if BORDER_RGB else ""
    lead = align_pad(inner + 2)

    print(f"{lead}{bc}{tl}{h * inner}{tr}{bce}")
    for idx, ln in enumerate(body):
        content = colored_body[idx]
        gap = " " * (width - visible_len(ln))
        print(f"{lead}{bc}{v}{bce}{' ' * pad}{content}{gap}{' ' * pad}{bc}{v}{bce}")
    print(f"{lead}{bc}{bl}{h * inner}{br}{bce}")
```

(`colored_body` is now 1:1 with `body` for every line — art rows, the blank separator, and the info line(s) — so the border path no longer needs the old `idx < len(colored)` branch.)

- [ ] **Step 5: Run the parity + generator tests**

Run: `.venv/bin/python -m pytest tests/test_parity.py tests/test_generator.py -q`
Expected: PASS — including the two inline-info parity cases and `test_info_style_baked`. If an info parity case fails on triple ORDER only (not the grid), reconcile the segmentation per the Step-1 note; never weaken the grid assertion.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, including `test_generated_banner_is_self_contained` (no third-party imports added).

- [ ] **Step 7: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/generator.py src/welchost/templates/welcome_banner.py.j2 tests/test_parity.py tests/test_generator.py
git commit -m "feat(generator): styled inline metadata in welcome_banner.py with parity"
```

---

## Task 6: Wizard step 1 — safe-font default, show-all, fit indicator, auto-fit

**Files:**
- Modify: `src/welchost/tui/screens/step_text_font.py`
- Test: `tests/test_wizard_rows.py`

**Interfaces:**
- Consumes: `welchost.fit.art_width`/`fits`/`auto_fit_font` (Task 2); `welchost.tui.fonts.SAFE_FONTS`/`safe_font_options`/`font_options` (Task 1); `app.model`.
- Produces: step-1 font Select defaulting to safe fonts; a `#show-all-fonts` Switch swapping the options to all fonts; a `#fit-indicator` Static showing `width N / target …`; an `#autofit` Button applying `auto_fit_font(model, SAFE_FONTS)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_wizard_rows.py`:

```python
async def test_show_all_fonts_toggle_expands_options(fake_home):
    detect.DEV_MODE = True
    from textual.widgets import Select, Switch

    from welchost.tui.fonts import SAFE_FONTS, all_fonts

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        font = app.screen.query_one("#font", Select)
        n_safe = len(list(font._options)) if hasattr(font, "_options") else None
        # default options are the safe set
        assert len(SAFE_FONTS) < len(all_fonts())
        app.screen.query_one("#show-all-fonts", Switch).value = True
        await pilot.pause()
        # after toggling, the option count grows to the full catalogue
        opts_after = [v for _, v in font._options]
        assert len(opts_after) >= len(all_fonts())


async def test_autofit_button_picks_a_fitting_font(fake_home):
    detect.DEV_MODE = True
    from welchost.fit import art_width

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        # Force a wide overflow then auto-fit.
        app.model.banner.rows[0].text = "WELCOME"
        app.model.banner.font = "colossal"
        app.model.banner.fit_width = 40
        app.screen.query_one("#text", __import__("textual.widgets", fromlist=["Input"]).Input).value = "WELCOME"
        await pilot.pause()
        app.screen.query_one("#autofit", __import__("textual.widgets", fromlist=["Button"]).Button).press()
        await pilot.pause()
        assert art_width(app.model, font=app.model.banner.font) <= 40
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_wizard_rows.py -q -k "show_all or autofit"`
Expected: FAIL — `#show-all-fonts`, `#fit-indicator`, `#autofit` don't exist yet.

- [ ] **Step 3: Implement step-1 controls**

Replace the body of `src/welchost/tui/screens/step_text_font.py` with:

```python
"""Wizard step 1 — stacked text rows + shared font + alignment + fit check."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Label, Select, Static, Switch

from ...config import Row
from ...fit import art_width, fits
from ...fit import auto_fit_font as _auto_fit
from ..fonts import SAFE_FONTS, font_options, safe_font_options

ALIGNMENTS = ["left", "center", "right"]


class StepTextFont(Vertical):
    """Edits the row texts, shared banner.font/align, with a live fit check."""

    title = "Step 1 · text + font + alignment"

    def compose(self) -> ComposeResult:
        m = self.app.model
        rows = m.banner.rows
        yield Label("banner text", classes="section-label")
        yield Input(rows[0].text, placeholder="Welcome", id="text")
        yield Label("second row  (optional · leave blank for one line)", classes="section-label")
        yield Input(rows[1].text if len(rows) > 1 else "", placeholder="(none)", id="text2")
        yield Label("font  (safe set · won't break)", classes="section-label")
        yield Select(self._font_opts(m.banner.font), id="font", value=m.banner.font, allow_blank=False)
        with Vertical(classes="info-row"):
            yield Switch(value=False, id="show-all-fonts")
            yield Label("show all fonts", classes="info-label")
        yield Static("", id="fit-indicator")
        yield Button("auto-fit font", id="autofit", compact=True)
        yield Label("alignment  (position on screen)", classes="section-label")
        yield Select([(a, a) for a in ALIGNMENTS], id="align", value=m.banner.align, allow_blank=False)

    def _show_all(self) -> bool:
        try:
            return self.query_one("#show-all-fonts", Switch).value
        except Exception:
            return False

    def _font_opts(self, current: str) -> list[tuple[str, str]]:
        opts = font_options() if self._show_all() else safe_font_options()
        if current not in {value for _, value in opts}:
            return [(current, current), *opts]
        return opts

    def load_from_model(self) -> None:
        m = self.app.model
        rows = m.banner.rows
        self.query_one("#text", Input).value = rows[0].text
        self.query_one("#text2", Input).value = rows[1].text if len(rows) > 1 else ""
        self.query_one("#align", Select).value = m.banner.align
        font_select = self.query_one("#font", Select)
        font_select.set_options(self._font_opts(m.banner.font))
        font_select.value = m.banner.font
        self._update_fit()

    def _update_fit(self) -> None:
        m = self.app.model
        target = m.banner.fit_width
        w = art_width(m)
        if target <= 0:
            text = f"[dim]width {w} · fit check off[/dim]"
        elif fits(m):
            text = f"[green]width {w} / {target} ✓[/green]"
        else:
            text = f"[yellow]width {w} / {target} ⚠ (try auto-fit)[/yellow]"
        self.query_one("#fit-indicator", Static).update(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        rows = self.app.model.banner.rows
        if event.input.id == "text":
            rows[0].text = event.value or "Welcome"
        elif event.input.id == "text2":
            self._set_second_row(event.value)
        self._update_fit()
        self.app.refresh_preview()

    def _set_second_row(self, text: str) -> None:
        rows = self.app.model.banner.rows
        if text.strip():
            if len(rows) > 1:
                rows[1].text = text
            else:
                rows.append(Row(text=text))
        elif len(rows) > 1:
            del rows[1:]

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is None:
            return
        if event.select.id == "font":
            self.app.model.banner.font = str(event.value)
            self._update_fit()
            self.app.refresh_preview()
        elif event.select.id == "align":
            self.app.model.banner.align = str(event.value)
            self.app.refresh_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "show-all-fonts":
            font_select = self.query_one("#font", Select)
            current = self.app.model.banner.font
            font_select.set_options(self._font_opts(current))
            font_select.value = current

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "autofit":
            chosen = _auto_fit(self.app.model, list(SAFE_FONTS))
            self.app.model.banner.font = chosen
            font_select = self.query_one("#font", Select)
            font_select.set_options(self._font_opts(chosen))
            font_select.value = chosen
            self._update_fit()
            self.app.refresh_preview()
```

- [ ] **Step 4: Run to verify the tests pass**

Run: `.venv/bin/python -m pytest tests/test_wizard_rows.py -q`
Expected: PASS (existing wizard tests + the two new ones).

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/tui/screens/step_text_font.py tests/test_wizard_rows.py
git commit -m "feat(tui): safe-font default, show-all toggle, fit indicator + auto-fit in step 1"
```

---

## Task 7: Wizard step 3 — metadata layout/separator/accent controls

**Files:**
- Modify: `src/welchost/tui/screens/step_decoration.py`
- Test: `tests/test_wizard_rows.py`

**Interfaces:**
- Consumes: `app.model.info` (`layout`/`separator`/`accent`); existing `Select`/`Input` widgets.
- Produces: a `#info-layout` Select (`inline`/`stacked`), a `#info-separator` Input, and a `#info-accent` Input (literal `auto` or a color), each mutating `app.model.info` and refreshing the preview.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_wizard_rows.py`:

```python
async def test_metadata_controls_mutate_model(fake_home):
    detect.DEV_MODE = True
    from textual.widgets import Input, Select

    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.action_next()  # step 2
        app.screen.action_next()  # step 3 (decoration + info)
        await pilot.pause()
        app.screen.query_one("#info-layout", Select).value = "stacked"
        app.screen.query_one("#info-separator", Input).value = "|"
        app.screen.query_one("#info-accent", Input).value = "#ff0000"
        await pilot.pause()
        assert app.model.info.layout == "stacked"
        assert app.model.info.separator == "|"
        assert app.model.info.accent == "#ff0000"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_wizard_rows.py -q -k metadata_controls`
Expected: FAIL — `#info-layout` / `#info-separator` / `#info-accent` don't exist.

- [ ] **Step 3: Add the metadata controls to step 3**

In `src/welchost/tui/screens/step_decoration.py`:

Add `Input` to the widget imports and `VALID_INFO_LAYOUTS` to the config import:

```python
from textual.widgets import Input, Label, Select, Switch

from ...config import VALID_INFO_LAYOUTS
```

In `compose`, after the info-widgets toggles loop, append the metadata-styling controls:

```python
        yield Label("metadata style", classes="section-label")
        yield Select(
            [(layout, layout) for layout in VALID_INFO_LAYOUTS],
            id="info-layout",
            value=m.info.layout,
            allow_blank=False,
        )
        yield Input(m.info.separator, placeholder="·", id="info-separator")
        yield Input(m.info.accent, placeholder="auto or #rrggbb", id="info-accent")
```

In `load_from_model`, after the info-toggle sync loop, add:

```python
        self.query_one("#info-layout", Select).value = m.info.layout
        self.query_one("#info-separator", Input).value = m.info.separator
        self.query_one("#info-accent", Input).value = m.info.accent
```

Extend `on_select_changed` to handle the layout select (add a branch):

```python
        elif event.select.id == "info-layout":
            self.app.model.info.layout = str(event.value)
            self.app.refresh_preview()
```

Add an `on_input_changed` handler (the step currently has none):

```python
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "info-separator":
            self.app.model.info.separator = event.value or "·"
            self.app.refresh_preview()
        elif event.input.id == "info-accent":
            self.app.model.info.accent = event.value or "auto"
            self.app.refresh_preview()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_wizard_rows.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`

```bash
git add src/welchost/tui/screens/step_decoration.py tests/test_wizard_rows.py
git commit -m "feat(tui): metadata layout/separator/accent controls in wizard step 3"
```

---

## Self-Review (completed during planning)

**Spec coverage (Phase 2 scope):**
- SAFE_FONTS set + picker default + "show all" → Tasks 1 (data) + 6 (wizard). ✓
- Design-time fit measurement + indicator + auto-fit → Tasks 2 (core) + 6 (wizard). ✓
- Styled inline metadata inheriting banner palette → Tasks 3 (config) + 4 (render) + 5 (generated, parity) + 7 (wizard controls). ✓
- WYSIWYG parity preserved → render + template move together logically; verified by `test_parity.py` info-ON cases (Task 5). ✓
- Lossless round-trip for new `[info]` fields → Task 3. ✓
- Deferred (documented): separator-boundary wrapping of an over-wide info row; runtime compact fallback (Phase 3).

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every test step shows assertions + expected pass/fail.

**Type consistency:** `art_width(cfg, font=None)`, `fits(cfg)`, `auto_fit_font(cfg, candidates)` used identically in Tasks 2 and 6. `Info.layout/separator/accent` defined in Task 3 and consumed by 4/5/7. `_info_style(config)` keys (`layout`, `separator`, `accent`, `value`) match the template's `INFO_STYLE[...]` reads in Task 5. `SAFE_FONTS`/`safe_font_options` defined in Task 1, consumed in 6. `_info_accent_rgb`/`_banner_color` (render.py) parallel `_info_style` (generator) — same auto-accent resolution rule (custom → border-if-set → first-row color), which is what keeps preview and generated in parity.
