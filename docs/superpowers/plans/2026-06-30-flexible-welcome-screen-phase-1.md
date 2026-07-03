# Flexible Welcome Screen — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Welchost banner be one or two **stacked rows** that share a font but each carry their own color/gradient, with full WYSIWYG parity between the live preview and the generated script, and with old configs auto-migrating.

**Architecture:** `[banner]` becomes a list of `rows` (each `text` + `color_mode` + `solid`/`gradient`); font, alignment, and a new `fit_width` stay shared on `[banner]`. The render pipeline (`render.py`) and the generated `welcome_banner.py` both iterate rows, coloring each row's figlet block independently, then stack them and wrap as today. Old flat configs migrate to a single row. A temporary set of read/write **compatibility shims** (`banner.text`, `banner.color_mode`, `config.solid`, `config.gradient` → `rows[0]`) keeps unmigrated consumers green between tasks; they are removed in the final task.

**Tech Stack:** Python 3.11+, dataclasses, `tomllib`/`tomli_w`, pyfiglet, Rich, Textual, Jinja2, pytest.

## Global Constraints

- **Min Python 3.11**; macOS-only.
- **WYSIWYG parity:** any render change lands in BOTH `src/welchost/render.py` AND `src/welchost/templates/welcome_banner.py.j2`; the gradient/color math must stay identical on both sides.
- **Lossless TOML round-trip** for new configs.
- **Generated `welcome_banner.py` has no third-party imports** (no `rich`, no `pyfiglet`) — pure-Python ANSI only.
- **Core stays Textual-free:** `src/welchost/{config,render,generator,themes,ornaments,detect}.py` must never `import` from `welchost.tui`.
- **All paths via `detect`**; all user output via Rich `Console`; always `mkdir -p` the config dir before writing.
- **Conventional commits**: `type(scope): description`. Phase-1 commits use `feat(...)`, `refactor(...)`, `test(...)` as fitting. Line length 100, `ruff` clean.
- Run the suite with `pytest`; lint with `ruff check src tests` and `ruff format --check src tests`.

---

## File Structure (Phase 1)

| File | Responsibility | Change |
|------|----------------|--------|
| `src/welchost/config.py` | Schema + dataclasses + load/save + migration | Add `Row`; rework `Banner`/`WelchostConfig`; rewrite `to_toml_dict`/`from_toml_dict`; bump `SCHEMA_VERSION`; add temp shims |
| `src/welchost/themes.py` | Built-in templates → config | Rewrite `Theme.to_config` to build a 1-row banner |
| `src/welchost/render.py` | Rich preview render (TUI + CLI) | `render_art` iterates rows; `_art_rows`/`_flank` take explicit color params |
| `src/welchost/generator.py` | Render generated files | `render_welcome_banner` passes a `rows` list |
| `src/welchost/templates/welcome_banner.py.j2` | Generated runtime renderer | Bake `ROWS`; loop + stack per-row coloring |
| `tests/test_config.py` | Config tests | Rewrite to rows API; add migration tests |
| `tests/test_themes.py` | Theme tests | Update attribute reads to `rows[0]` |
| `tests/test_render.py` (new) | Render-pipeline tests | Multi-row + per-row color assertions |
| `tests/test_generator.py` | Generation tests | Update to rows API; add 2-row generation test |
| `src/welchost/tui/screens/step_text_font.py` | Wizard step 1 | Add optional second-row text input |
| `src/welchost/tui/screens/step_color.py` | Wizard step 2 | Per-row color controls |
| `tests/test_wizard_rows.py` (new) | Wizard tests | Second row add/trim + per-row color |

---

## Task 1: Rows data model, migration, and shims

**Files:**
- Modify: `src/welchost/config.py`
- Modify: `src/welchost/themes.py`
- Test: `tests/test_config.py`, `tests/test_themes.py`

**Interfaces:**
- Produces:
  - `Row(text: str = "Welcome", color_mode: str = "solid", solid: SolidColor, gradient: GradientColor)`
  - `Banner(font: str = "slant", align: str = "left", fit_width: int = 80, rows: list[Row])` with temporary read/write properties `text` and `color_mode` proxying `rows[0]`.
  - `WelchostConfig(banner, decoration, ornament, info, meta)` with temporary read properties `solid`/`gradient` proxying `banner.rows[0]`.
  - `WelchostConfig.to_toml_dict()` emits `banner.rows` as an array of tables.
  - `WelchostConfig.from_toml_dict(data)` builds rows, migrating legacy flat configs to a single row.
  - `SCHEMA_VERSION == "2.0.0"`.
- Consumes: nothing new.

- [ ] **Step 1: Write failing tests for the rows model + migration**

Replace the body of `tests/test_config.py` with:

```python
"""Tests for config load/save, round-trip, and legacy migration."""

from __future__ import annotations

from welchost import detect
from welchost.config import (
    GradientColor,
    Row,
    SolidColor,
    WelchostConfig,
    load_config,
    save_config,
)


def test_load_missing_returns_none(fake_home):
    assert load_config() is None


def test_default_has_single_row(fake_home):
    cfg = WelchostConfig.default()
    assert len(cfg.banner.rows) == 1
    assert cfg.banner.rows[0].text == "Welcome"
    assert cfg.banner.rows[0].color_mode == "solid"
    assert cfg.banner.font == "slant"
    assert cfg.banner.align == "left"
    assert cfg.banner.fit_width == 80


def test_two_row_roundtrip_is_lossless(fake_home):
    cfg = WelchostConfig.default()
    cfg.banner.font = "ansi_shadow"
    cfg.banner.rows = [
        Row(text="JAKUB", color_mode="solid", solid=SolidColor(value="#d97757")),
        Row(
            text="SALMIK",
            color_mode="gradient",
            gradient=GradientColor(start="cyan", end="magenta", direction="horizontal"),
        ),
    ]
    save_config(cfg)

    loaded = load_config()
    assert loaded is not None
    assert loaded.banner.font == "ansi_shadow"
    assert [r.text for r in loaded.banner.rows] == ["JAKUB", "SALMIK"]
    assert loaded.banner.rows[0].color_mode == "solid"
    assert loaded.banner.rows[0].solid.value == "#d97757"
    assert loaded.banner.rows[1].color_mode == "gradient"
    assert loaded.banner.rows[1].gradient.start == "cyan"
    assert loaded.banner.rows[1].gradient.end == "magenta"
    assert loaded.banner.rows[1].gradient.direction == "horizontal"


def test_legacy_flat_config_migrates_to_one_row(fake_home):
    # A pre-2.0 welchost.toml: text + color_mode on [banner], color in [color.*].
    legacy = {
        "banner": {"text": "Hi there", "font": "doom", "align": "center", "color_mode": "gradient"},
        "color": {
            "solid": {"value": "cyan"},
            "gradient": {"start": "#ff6b35", "end": "#f7c59f", "direction": "diagonal"},
        },
    }
    cfg = WelchostConfig.from_toml_dict(legacy)
    assert cfg.banner.font == "doom"
    assert cfg.banner.align == "center"
    assert len(cfg.banner.rows) == 1
    row = cfg.banner.rows[0]
    assert row.text == "Hi there"
    assert row.color_mode == "gradient"
    assert row.gradient.start == "#ff6b35"
    assert row.gradient.end == "#f7c59f"
    assert row.gradient.direction == "diagonal"


def test_legacy_size_key_is_ignored(fake_home):
    # The long-removed `banner.size` must not crash the loader.
    cfg = WelchostConfig.from_toml_dict(
        {"banner": {"text": "Hi", "font": "slant", "size": "xl", "color_mode": "solid"}}
    )
    assert cfg.banner.rows[0].text == "Hi"
    assert cfg.banner.align == "left"
    assert not hasattr(cfg.banner, "size")


def test_compat_shims_proxy_first_row(fake_home):
    # Temporary shims (removed in Task 6) let unmigrated callers read/write row 0.
    cfg = WelchostConfig.default()
    cfg.banner.text = "Shimmed"
    cfg.banner.color_mode = "gradient"
    cfg.solid.value = "red"
    cfg.gradient.start = "blue"
    assert cfg.banner.rows[0].text == "Shimmed"
    assert cfg.banner.rows[0].color_mode == "gradient"
    assert cfg.banner.rows[0].solid.value == "red"
    assert cfg.banner.rows[0].gradient.start == "blue"


def test_save_stamps_created_at_and_version(fake_home):
    cfg = WelchostConfig.default()
    assert cfg.meta.created_at == ""
    save_config(cfg)
    loaded = load_config()
    assert loaded.meta.created_at != ""
    assert loaded.meta.welchost_version == "2.0.0"


def test_save_creates_config_dir(fake_home):
    assert not detect.get_config_dir().exists()
    save_config(WelchostConfig.default())
    assert detect.get_config_path().exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_config.py -q`
Expected: FAIL — `ImportError: cannot import name 'Row'` (and the rows attributes don't exist yet).

- [ ] **Step 3: Implement the new schema in `config.py`**

In `src/welchost/config.py`, bump the version and add the `Row` dataclass + reworked `Banner`/`WelchostConfig`. Replace the `SCHEMA_VERSION` line and the `Banner`, `WelchostConfig` dataclasses and the (de)serialization methods.

Set the version:

```python
SCHEMA_VERSION = "2.0.0"
```

Replace the `Banner` dataclass with `Row` + the new `Banner`:

```python
@dataclass
class Row:
    """One stacked banner line: its text and its own color treatment."""

    text: str = "Welcome"
    color_mode: str = "solid"  # solid | gradient
    solid: SolidColor = field(default_factory=SolidColor)
    gradient: GradientColor = field(default_factory=GradientColor)


@dataclass
class Banner:
    font: str = "slant"
    align: str = "left"
    fit_width: int = 80  # target width for fit checks (0 disables)
    rows: list[Row] = field(default_factory=lambda: [Row()])

    # --- TEMPORARY single-row compatibility shims (removed in Phase-1 Task 6) ---
    # Let consumers that still read/write the old flat fields keep working against
    # row 0 until they are migrated to the rows API.
    @property
    def text(self) -> str:
        return self.rows[0].text

    @text.setter
    def text(self, value: str) -> None:
        self.rows[0].text = value

    @property
    def color_mode(self) -> str:
        return self.rows[0].color_mode

    @color_mode.setter
    def color_mode(self, value: str) -> None:
        self.rows[0].color_mode = value
```

Note: `SolidColor` and `GradientColor` dataclasses stay exactly as they are. Move the `Row` definition **below** `SolidColor`/`GradientColor` so the `field(default_factory=...)` references resolve.

Replace the `WelchostConfig` dataclass and its serialization methods with:

```python
@dataclass
class WelchostConfig:
    """In-memory representation of welchost.toml."""

    banner: Banner = field(default_factory=Banner)
    decoration: Decoration = field(default_factory=Decoration)
    ornament: Ornament = field(default_factory=Ornament)
    info: Info = field(default_factory=Info)
    meta: Meta = field(default_factory=Meta)

    @classmethod
    def default(cls) -> WelchostConfig:
        return cls()

    # --- TEMPORARY compatibility shims (removed in Phase-1 Task 6) ---
    @property
    def solid(self) -> SolidColor:
        return self.banner.rows[0].solid

    @property
    def gradient(self) -> GradientColor:
        return self.banner.rows[0].gradient

    # -- (de)serialization -------------------------------------------------

    def to_toml_dict(self) -> dict:
        """Build the nested dict matching the TOML layout."""
        return {
            "banner": {
                "font": self.banner.font,
                "align": self.banner.align,
                "fit_width": self.banner.fit_width,
                "rows": [
                    {
                        "text": r.text,
                        "color_mode": r.color_mode,
                        "solid": asdict(r.solid),
                        "gradient": asdict(r.gradient),
                    }
                    for r in self.banner.rows
                ],
            },
            "decoration": asdict(self.decoration),
            "ornament": asdict(self.ornament),
            "info": asdict(self.info),
            "meta": asdict(self.meta),
        }

    @classmethod
    def from_toml_dict(cls, data: dict) -> WelchostConfig:
        banner_data = data.get("banner", {})
        rows = _build_rows(banner_data, data.get("color", {}))
        banner = Banner(
            font=banner_data.get("font", "slant"),
            align=banner_data.get("align", "left"),
            fit_width=int(banner_data.get("fit_width", 80)),
            rows=rows,
        )
        return cls(
            banner=banner,
            decoration=_build(Decoration, data.get("decoration", {})),
            ornament=_build(Ornament, data.get("ornament", {})),
            info=_build(Info, data.get("info", {})),
            meta=_build(Meta, data.get("meta", {})),
        )
```

Add the `_build_rows` helper just above `WelchostConfig` (after `_build`):

```python
def _build_row(row: dict) -> Row:
    return Row(
        text=row.get("text", "Welcome"),
        color_mode=row.get("color_mode", "solid"),
        solid=_build(SolidColor, row.get("solid", {})),
        gradient=_build(GradientColor, row.get("gradient", {})),
    )


def _build_rows(banner_data: dict, color_data: dict) -> list[Row]:
    """Build the row list, migrating a legacy flat banner to a single row.

    New configs carry ``banner.rows``. A pre-2.0 config has ``banner.text`` +
    ``banner.color_mode`` and top-level ``[color.solid]`` / ``[color.gradient]``;
    fold those into one row so old installs keep working.
    """
    raw_rows = banner_data.get("rows")
    if raw_rows:
        return [_build_row(r) for r in raw_rows]
    if "text" in banner_data:
        return [
            Row(
                text=banner_data.get("text", "Welcome"),
                color_mode=banner_data.get("color_mode", "solid"),
                solid=_build(SolidColor, color_data.get("solid", {})),
                gradient=_build(GradientColor, color_data.get("gradient", {})),
            )
        ]
    return [Row()]
```

- [ ] **Step 4: Run config tests to verify they pass**

Run: `pytest tests/test_config.py -q`
Expected: PASS (all tests).

- [ ] **Step 5: Update `themes.py` to build a 1-row banner**

In `src/welchost/themes.py`, replace the `to_config` method body (it currently passes `text=`/`color_mode=` to `Banner` and `solid=`/`gradient=` to `WelchostConfig`, which no longer accept those):

```python
    def to_config(self, text: str = "Welcome") -> WelchostConfig:
        color_mode = "gradient" if self.is_gradient else "solid"
        solid = SolidColor(value=self.color or "cyan")
        gradient = GradientColor(
            start=self.gradient_start or "cyan",
            end=self.gradient_end or "magenta",
            direction=self.gradient_direction,
        )
        row = Row(text=text, color_mode=color_mode, solid=solid, gradient=gradient)
        return WelchostConfig(
            banner=Banner(font=self.font, rows=[row]),
            decoration=Decoration(border_style=self.border_style, border_color=self.border_color),
            ornament=Ornament(name=self.ornament),
            info=Info(),
        )
```

Update the import at the top of `themes.py` to include `Row`:

```python
from .config import (
    Banner,
    Decoration,
    GradientColor,
    Info,
    Ornament,
    Row,
    SolidColor,
    WelchostConfig,
)
```

- [ ] **Step 6: Update `tests/test_themes.py` attribute reads**

In `tests/test_themes.py`, the two assertions that read the old flat attributes must read `rows[0]`. Replace `test_theme_converts_to_config`:

```python
@pytest.mark.parametrize("theme", all_themes(), ids=lambda t: t.name)
def test_theme_converts_to_config(theme):
    cfg = theme.to_config(text="Hi")
    assert cfg.banner.rows[0].text == "Hi"
    assert cfg.banner.font == theme.font
    assert cfg.decoration.border_style == theme.border_style
    if theme.is_gradient:
        assert cfg.banner.rows[0].color_mode == "gradient"
    else:
        assert cfg.banner.rows[0].color_mode == "solid"
```

And replace `test_sunset_is_gradient`:

```python
def test_sunset_is_gradient():
    sunset = get_theme("sunset")
    assert sunset is not None
    assert sunset.is_gradient
    cfg = sunset.to_config()
    assert cfg.banner.rows[0].gradient.start == "#ff6b35"
    assert cfg.banner.rows[0].gradient.end == "#f7c59f"
```

- [ ] **Step 7: Run the full suite (shims keep render/generator/wizard green)**

Run: `pytest -q`
Expected: PASS. `render.py`, `generator.py`, and the wizard still read `cfg.banner.text` / `cfg.banner.color_mode` / `cfg.solid` / `cfg.gradient` through the temporary shims, so nothing else breaks yet.

- [ ] **Step 8: Lint and commit**

Run: `ruff check src tests && ruff format --check src tests`
Expected: clean.

```bash
git add src/welchost/config.py src/welchost/themes.py tests/test_config.py tests/test_themes.py
git commit -m "feat(config): model banner as stacked rows with per-row color + legacy migration"
```

---

## Task 2: Multi-row rendering in `render.py`

**Files:**
- Modify: `src/welchost/render.py`
- Test: `tests/test_render.py` (create)

**Interfaces:**
- Consumes: `WelchostConfig.banner.rows` (list of `Row`), `banner.font`, `Row.color_mode`/`solid`/`gradient` (from Task 1).
- Produces: `render_art(cfg)` returns a Rich `Text` of all rows stacked (one blank line between rows), each colored by its own row config; `render_banner(cfg)` unchanged signature.

- [ ] **Step 1: Write failing render tests**

Create `tests/test_render.py`:

```python
"""Tests for the Rich render pipeline (multi-row, per-row color)."""

from __future__ import annotations

from welchost.config import GradientColor, Row, SolidColor, WelchostConfig
from welchost.render import render_art


def _one_row(text="Hi", font="standard"):
    cfg = WelchostConfig.default()
    cfg.banner.font = font
    cfg.banner.rows = [Row(text=text)]
    return cfg


def test_two_rows_are_taller_than_one(fake_home):
    one = render_art(_one_row("Hi")).plain.split("\n")
    cfg = _one_row("Hi")
    cfg.banner.rows = [Row(text="Hi"), Row(text="Yo")]
    two = render_art(cfg).plain.split("\n")
    # Two stacked blocks + one blank separator row are strictly taller.
    assert len(two) > len(one)


def test_two_rows_separated_by_blank_line(fake_home):
    cfg = _one_row("Hi")
    cfg.banner.rows = [Row(text="Hi"), Row(text="Yo")]
    lines = render_art(cfg).plain.split("\n")
    assert any(ln.strip() == "" for ln in lines), "expected a blank separator between rows"


def test_each_row_uses_its_own_color(fake_home):
    cfg = _one_row("Hi")
    cfg.banner.rows = [
        Row(text="Hi", color_mode="solid", solid=SolidColor(value="red")),
        Row(text="Yo", color_mode="solid", solid=SolidColor(value="blue")),
    ]
    styles = {str(span.style) for span in render_art(cfg).spans}
    # red -> rgb(197,15,31); blue -> rgb(0,55,218) (generator.NAMED_COLORS).
    assert any("197,15,31" in s for s in styles), "row 1 red missing"
    assert any("0,55,218" in s for s in styles), "row 2 blue missing"


def test_single_row_still_renders(fake_home):
    assert render_art(_one_row("Hi")).plain.strip()
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_render.py -q`
Expected: FAIL — `test_two_rows_*` fail because `render_art` only renders `rows[0]` via the shim (single block).

- [ ] **Step 3: Refactor `render.py` to iterate rows**

In `src/welchost/render.py`, change `_art_rows` to take explicit color params instead of reading `cfg`, add a per-row block builder, and rewrite `render_art`. Replace `_art_rows`:

```python
def _art_rows(
    lines: list[str],
    color_mode: str,
    solid_value: str,
    grad_start: str,
    grad_end: str,
    direction: str,
) -> list[Text]:
    """One styled Text per art line (gradient or solid) for a single row block."""
    rows: list[Text] = []
    if color_mode == "gradient":
        s = resolve_color(grad_start)
        e = resolve_color(grad_end)
        dx = max(max((len(ln) for ln in lines), default=1) - 1, 1)
        dy = max(len(lines) - 1, 1)
        for row, line in enumerate(lines):
            tx = Text()
            for col, ch in enumerate(line):
                f = _gradient_factor(col, row, dx, dy, direction)
                r, g, b = _blend(s, e, f)
                tx.append(ch, style=f"bold rgb({r},{g},{b})")
            rows.append(tx)
    else:
        r, g, b = resolve_color(solid_value)
        rows = [Text(line, style=f"bold rgb({r},{g},{b})") for line in lines]
    return rows
```

Add a helper that builds one row's colored Text lines, and rewrite `render_art`:

```python
def _row_block(cfg: WelchostConfig, row) -> list[Text]:
    """Colored Text lines for a single banner row, rendered in the shared font."""
    art = _render_figlet(cfg.banner.font, row.text)
    lines = _strip_blank_edges(art.splitlines())
    return _art_rows(
        lines,
        row.color_mode,
        row.solid.value,
        row.gradient.start,
        row.gradient.end,
        row.gradient.direction,
    )


def render_art(cfg: WelchostConfig) -> Text:
    """The colored figlet block(s), stacked one row per banner row (blank line
    between), optionally flanked by an ornament. Each row is colored by its own
    row config; gradients run within each row's own block."""
    stacked: list[Text] = []
    for i, row in enumerate(cfg.banner.rows):
        if i:
            stacked.append(Text(""))  # blank separator between stacked rows
        stacked.extend(_row_block(cfg, row))

    rows = _flank(stacked, cfg)

    block = Text()
    for i, row in enumerate(rows):
        block.append_text(row)
        if i != len(rows) - 1:
            block.append("\n")
    return block
```

Add the `_render_figlet` import near the top of `render.py` (it lives in `generator`):

```python
from .generator import build_figlet, resolve_color, _render_figlet
```

Update `_flank` so the ornament color comes from the **first row** instead of the removed top-level fields. Replace the `color = ...` line inside `_flank`:

```python
    first = cfg.banner.rows[0]
    color = first.gradient.start if first.color_mode == "gradient" else first.solid.value
```

`build_figlet` and the `_strip_blank_edges`/`_blend`/`_gradient_factor` helpers stay as they are. `render_banner` is unchanged (it calls `render_art` then appends `info_text`).

- [ ] **Step 4: Run render tests to verify they pass**

Run: `pytest tests/test_render.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS (generator still uses shims; nothing else regressed).

- [ ] **Step 6: Lint and commit**

Run: `ruff check src tests && ruff format --check src tests`

```bash
git add src/welchost/render.py tests/test_render.py
git commit -m "feat(render): stack and color banner rows independently in the preview"
```

---

## Task 3: Multi-row generation in `generator.py` + template

**Files:**
- Modify: `src/welchost/generator.py`
- Modify: `src/welchost/templates/welcome_banner.py.j2`
- Test: `tests/test_generator.py`

**Interfaces:**
- Consumes: `cfg.banner.rows`, `cfg.banner.font`, `resolve_color`, `_render_figlet`.
- Produces: generated `welcome_banner.py` whose module global `ROWS` is a `list[dict]` (one per banner row) and whose `render()` stacks them with per-row coloring, producing output identical to `render.py`.

- [ ] **Step 1: Update failing generator tests**

In `tests/test_generator.py`, two existing tests use the removed flat fields and must move to the rows API; add one new 2-row test. Replace `test_gradient_direction_baked_into_banner`:

```python
def test_gradient_direction_baked_into_banner(fake_home):
    cfg = WelchostConfig.default()
    cfg.banner.rows[0].color_mode = "gradient"
    cfg.banner.rows[0].gradient.direction = "diagonal"
    _, banner = generator.write_generated_files(cfg)
    assert '"grad_dir": "diagonal"' in banner.read_text()
```

Replace `test_ornament_baked_and_renders`:

```python
def test_ornament_baked_and_renders(fake_home):
    cfg = WelchostConfig.default()
    cfg.banner.rows[0].text = "Hi"
    cfg.ornament.name = "ghosts"
    _, banner = generator.write_generated_files(cfg)
    src = banner.read_text()
    assert "ORN_LEFT = " in src
    assert ")(" in src  # the ghost ornament glyphs are baked in
    ns = {"__name__": "not_main"}
    exec(compile(src, "welcome_banner.py", "exec"), ns)
    ns["render"]()
```

Add a new test after it:

```python
def test_two_rows_baked_and_render(fake_home):
    from welchost.config import Row, SolidColor

    cfg = WelchostConfig.default()
    cfg.banner.font = "standard"
    cfg.banner.rows = [
        Row(text="JAKUB", color_mode="solid", solid=SolidColor(value="red")),
        Row(text="SALMIK", color_mode="solid", solid=SolidColor(value="blue")),
    ]
    _, banner = generator.write_generated_files(cfg)
    src = banner.read_text()
    ns = {"__name__": "not_main"}
    exec(compile(src, "welcome_banner.py", "exec"), ns)
    assert len(ns["ROWS"]) == 2
    assert ns["ROWS"][0]["color_mode"] == "solid"
    ns["render"]()  # must not raise
```

`test_build_figlet_nonempty` and `test_build_figlet_invalid_font_falls_back` stay (they call `generator.build_figlet(cfg)`, which still renders `rows[0]` via the shim — keep `build_figlet` as-is).

- [ ] **Step 2: Run to verify the changed tests fail**

Run: `pytest tests/test_generator.py -q`
Expected: FAIL — the template still bakes a single `ART`/`GRAD_DIR`; `"grad_dir"` and `ROWS` don't exist yet.

- [ ] **Step 3: Pass a `rows` list from the generator**

In `src/welchost/generator.py`, replace `render_welcome_banner` with a version that builds a per-row list and drops the single-art scalars:

```python
def render_welcome_banner(config: WelchostConfig) -> str:
    # Clamp every enum baked as a raw string into the generated Python source.
    align = _enum(config.banner.align, VALID_ALIGN, "left")
    border_style = _enum(config.decoration.border_style, VALID_BORDER_STYLES, "none")
    border_rgb = None if border_style == "none" else resolve_color(config.decoration.border_color)

    rows = []
    for row in config.banner.rows:
        rows.append(
            {
                "art": _render_figlet(config.banner.font, row.text),
                "color_mode": _enum(row.color_mode, VALID_COLOR_MODES, "solid"),
                "solid": resolve_color(row.solid.value),
                "grad_start": resolve_color(row.gradient.start),
                "grad_end": resolve_color(row.gradient.end),
                "grad_dir": _enum(row.gradient.direction, VALID_GRADIENT_DIRECTIONS, "horizontal"),
            }
        )

    first = config.banner.rows[0]
    orn_left, orn_right = get_ornament(config.ornament.name)
    orn_color = first.gradient.start if first.color_mode == "gradient" else first.solid.value
    orn_rgb = resolve_color(orn_color) if (orn_left or orn_right) else None
    template = _env().get_template("welcome_banner.py.j2")
    return template.render(
        version=__version__,
        rows=repr(rows),
        align=align,
        border_style=border_style,
        border_rgb=repr(border_rgb),
        orn_left=json.dumps(orn_left),
        orn_right=json.dumps(orn_right),
        orn_rgb=repr(orn_rgb),
        info=repr(_info_dict(config)),
    )
```

(`repr(rows)` is safe to embed: every value is a clamped enum string, an `(int,int,int)` tuple, or pyfiglet art text — `repr` escapes it as a Python literal. The enum clamps close the same injection vector `_enum` already guards.)

- [ ] **Step 4: Rewrite the generated-renderer template**

Replace the whole contents of `src/welchost/templates/welcome_banner.py.j2` with:

```jinja
#!/usr/bin/env python3
# Generated by welchost {{ version }} - DO NOT EDIT.
# This file is regenerated from ~/.config/ghostty/welchost.toml.
# Edit the TOML and run `welchost config`; never edit this script directly.
#
# Self-contained: pure-Python ANSI rendering, no third-party imports, so it runs
# under whatever `python3` Ghostty's shell finds.
import getpass
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime

# --- baked-in config (from welchost.toml) -----------------------------------
# ROWS: one dict per stacked banner row.
ROWS = {{ rows }}
ALIGN = "{{ align }}"
BORDER_STYLE = "{{ border_style }}"
BORDER_RGB = {{ border_rgb }}
ORN_LEFT = {{ orn_left }}
ORN_RIGHT = {{ orn_right }}
ORN_RGB = {{ orn_rgb }}
INFO = {{ info }}

RESET = "\x1b[0m"

BORDERS = {
    "panel": "┏━┓┃┗┛",
    "box": "┌─┐│└┘",
    "rounded": "╭─╮│╰╯",
    "double": "╔═╗║╚╝",
    "ascii": "+-+|+-+|",
}


def fg(rgb):
    r, g, b = rgb
    return f"\x1b[1;38;2;{r};{g};{b}m"


def _factor(col, row, dx, dy, direction):
    # Position 0→1 of a character within the block, per gradient direction.
    if direction == "vertical":
        return row / dy
    if direction == "diagonal":
        return (col / dx + row / dy) / 2
    return col / dx  # horizontal (default)


def colorize_block(lines, cfg):
    # Color one row's art block by its own mode/colors. Returns colored lines.
    mode = cfg["color_mode"]
    if mode == "gradient":
        gs, ge, gd = cfg["grad_start"], cfg["grad_end"], cfg["grad_dir"]
        dx = max(max((len(ln) for ln in lines), default=1) - 1, 1)
        dy = max(len(lines) - 1, 1)
        out = []
        for row, line in enumerate(lines):
            if not line:
                out.append(line)
                continue
            chars = []
            for col, ch in enumerate(line):
                t = _factor(col, row, dx, dy, gd)
                r = round(gs[0] + (ge[0] - gs[0]) * t)
                g = round(gs[1] + (ge[1] - gs[1]) * t)
                b = round(gs[2] + (ge[2] - gs[2]) * t)
                chars.append(f"\x1b[1;38;2;{r};{g};{b}m{ch}")
            out.append("".join(chars) + RESET)
        return out
    sc = fg(cfg["solid"])
    return [(sc + line + RESET) if line else line for line in lines]


def _strip_block(art):
    lines = art.splitlines()
    while lines and lines[-1].strip() == "":
        lines.pop()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    return lines


def build_rows():
    # Returns (plain_lines, colored_lines): the stacked art for all rows with one
    # blank separator between rows. Plain lines are used for width/border math.
    plain, colored = [], []
    for i, cfg in enumerate(ROWS):
        if i:
            plain.append("")
            colored.append("")
        block = _strip_block(cfg["art"])
        plain.extend(block)
        colored.extend(colorize_block(block, cfg))
    return plain, colored


def visible_len(s):
    # length of the raw (uncolored) string; plain lines are stored uncolored
    return len(s)


def align_pad(box_width):
    if ALIGN == "left":
        return ""
    import shutil

    try:
        cols = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        cols = 80
    space = max(cols - box_width, 0)
    if ALIGN == "center":
        return " " * (space // 2)
    if ALIGN == "right":
        return " " * space
    return ""


def flank(art_lines, colored, artw):
    lw = max((len(s) for s in ORN_LEFT), default=0)
    rw = max((len(s) for s in ORN_RIGHT), default=0)
    total = max(len(art_lines), len(ORN_LEFT), len(ORN_RIGHT))
    a_off = (total - len(art_lines)) // 2
    l_off = (total - len(ORN_LEFT)) // 2
    r_off = (total - len(ORN_RIGHT)) // 2
    oc = fg(ORN_RGB) if ORN_RGB else ""
    oce = RESET if ORN_RGB else ""
    gap = "   "
    plain, disp = [], []
    for i in range(total):
        ls = ORN_LEFT[i - l_off] if 0 <= i - l_off < len(ORN_LEFT) else ""
        rs = ORN_RIGHT[i - r_off] if 0 <= i - r_off < len(ORN_RIGHT) else ""
        ai = i - a_off
        art_p = art_lines[ai] if 0 <= ai < len(art_lines) else ""
        art_d = colored[ai] if 0 <= ai < len(colored) else ""
        p, d = "", ""
        if lw:
            p += ls.ljust(lw) + gap
            d += oc + ls.ljust(lw) + oce + gap
        p += art_p.ljust(artw)
        d += art_d + " " * (artw - len(art_p))
        if rw:
            p += gap + rs.ljust(rw)
            d += gap + oc + rs.ljust(rw) + oce
        plain.append(p)
        disp.append(d)
    return plain, disp


def info_lines():
    lines = []
    if INFO.get("show_user"):
        lines.append(("user", getpass.getuser()))
    if INFO.get("show_host"):
        lines.append(("host", socket.gethostname()))
    if INFO.get("show_os"):
        mac = platform.mac_ver()[0]
        osname = f"macOS {mac}" if mac else platform.platform(terse=True)
        lines.append(("os", osname))
    if INFO.get("show_datetime"):
        lines.append(("date", datetime.now().strftime("%a %d %b %Y · %H:%M")))
    if INFO.get("show_uptime"):
        lines.append(("uptime", _uptime()))
    if INFO.get("show_shell"):
        lines.append(("shell", os.environ.get("SHELL", "?")))
    if INFO.get("show_python"):
        lines.append(("python", platform.python_version()))
    if INFO.get("show_ip"):
        lines.append(("ip", _local_ip()))
    return [f"{k}: {v}" for k, v in lines]


def _uptime():
    try:
        out = subprocess.run(["uptime"], capture_output=True, text=True, timeout=2).stdout
        if "up" in out:
            return out.split("up", 1)[1].split(",")[0].strip()
    except Exception:
        pass
    return "?"


def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"


def render():
    art_lines, colored = build_rows()
    artw = max((visible_len(ln) for ln in art_lines), default=0)

    if ORN_LEFT or ORN_RIGHT:
        art_lines, colored = flank(art_lines, colored, artw)

    extra = info_lines()
    body = list(art_lines)
    if extra:
        body.append("")
        body.extend(extra)

    width = max((visible_len(ln) for ln in body), default=0)

    if BORDER_STYLE == "none":
        lead = align_pad(width)
        for ln in colored:
            print(lead + ln)
        for ln in extra:
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
        content = colored[idx] if idx < len(colored) else ln
        gap = " " * (width - visible_len(ln))
        print(f"{lead}{bc}{v}{bce}{' ' * pad}{content}{gap}{' ' * pad}{bc}{v}{bce}")
    print(f"{lead}{bc}{bl}{h * inner}{br}{bce}")


if __name__ == "__main__":
    try:
        render()
    except Exception as exc:  # never break the shell on a banner error
        sys.stderr.write(f"welchost banner error: {exc}\n")
```

- [ ] **Step 5: Run generator tests to verify they pass**

Run: `pytest tests/test_generator.py -q`
Expected: PASS — including `test_generated_banner_is_self_contained` (no `rich`/`pyfiglet` imports) and `test_two_rows_baked_and_render`.

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 7: Lint and commit**

Run: `ruff check src tests && ruff format --check src tests`

```bash
git add src/welchost/generator.py src/welchost/templates/welcome_banner.py.j2 tests/test_generator.py
git commit -m "feat(generator): bake and render stacked rows in welcome_banner.py"
```

---

## Task 4: Wizard step 1 — optional second row

**Files:**
- Modify: `src/welchost/tui/screens/step_text_font.py`
- Test: `tests/test_wizard_rows.py` (create)

**Interfaces:**
- Consumes: `app.model.banner.rows`, `Row` from `welchost.config`.
- Produces: a `#text2` input on step 1; typing into it appends a second `Row`, clearing it trims back to one row. Row 1 text edits `rows[0].text`; the shared font/alignment behavior is unchanged.

- [ ] **Step 1: Write the failing wizard test**

Create `tests/test_wizard_rows.py`:

```python
"""Wizard support for a second stacked row."""

from __future__ import annotations

from textual.widgets import Input

from welchost import detect
from welchost.tui.app import WelchostApp
from welchost.tui.screens.wizard import Wizard


async def test_typing_second_row_adds_a_row(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.query_one("#text2", Input).value = "SALMIK"
        await pilot.pause()
        assert len(app.model.banner.rows) == 2
        assert app.model.banner.rows[1].text == "SALMIK"


async def test_clearing_second_row_trims_back_to_one(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        text2 = app.screen.query_one("#text2", Input)
        text2.value = "SALMIK"
        await pilot.pause()
        text2.value = ""
        await pilot.pause()
        assert len(app.model.banner.rows) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_wizard_rows.py -q`
Expected: FAIL — `NoMatches: #text2` (the input doesn't exist yet).

- [ ] **Step 3: Add the second-row input + handlers**

Replace the body of `src/welchost/tui/screens/step_text_font.py` with:

```python
"""Wizard step 1 — stacked text rows + shared font + alignment."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select

from ...config import Row
from ..fonts import font_options

ALIGNMENTS = ["left", "center", "right"]


class StepTextFont(Vertical):
    """Edits the row texts, shared banner.font and banner.align on app.model."""

    title = "Step 1 · text + font + alignment"

    def compose(self) -> ComposeResult:
        m = self.app.model
        rows = m.banner.rows
        yield Label("banner text", classes="section-label")
        yield Input(rows[0].text, placeholder="Welcome", id="text")
        yield Label("second row  (optional · leave blank for one line)", classes="section-label")
        yield Input(rows[1].text if len(rows) > 1 else "", placeholder="(none)", id="text2")
        yield Label("font  (type to jump · curated first)", classes="section-label")
        yield Select(
            self._font_opts(m.banner.font), id="font", value=m.banner.font, allow_blank=False
        )
        yield Label("alignment  (position on screen)", classes="section-label")
        yield Select(
            [(a, a) for a in ALIGNMENTS], id="align", value=m.banner.align, allow_blank=False
        )

    @staticmethod
    def _font_opts(current: str) -> list[tuple[str, str]]:
        opts = font_options()
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

    def on_input_changed(self, event: Input.Changed) -> None:
        rows = self.app.model.banner.rows
        if event.input.id == "text":
            rows[0].text = event.value or "Welcome"
        elif event.input.id == "text2":
            self._set_second_row(event.value)
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
            self.app.refresh_preview()
        elif event.select.id == "align":
            self.app.model.banner.align = str(event.value)
            self.app.refresh_preview()
```

- [ ] **Step 4: Run wizard tests to verify they pass**

Run: `pytest tests/test_wizard_rows.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

Run: `ruff check src tests && ruff format --check src tests`

```bash
git add src/welchost/tui/screens/step_text_font.py tests/test_wizard_rows.py
git commit -m "feat(tui): add an optional second banner row to wizard step 1"
```

---

## Task 5: Wizard step 2 — per-row color

**Files:**
- Modify: `src/welchost/tui/screens/step_color.py`
- Test: `tests/test_wizard_rows.py` (extend)

**Interfaces:**
- Consumes: `app.model.banner.rows`, each `Row.color_mode`/`solid`/`gradient`; `ColorField`, `apply_visibility` from `..widgets`.
- Produces: step 2 shows a color group for row 1 always and for row 2 only when two rows exist; editing each group mutates that row's color. Control ids are suffixed `-0` / `-1` per row.

- [ ] **Step 1: Write the failing per-row color test**

Append to `tests/test_wizard_rows.py`:

```python
async def test_second_row_color_is_independent(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        # Add a second row in step 1.
        app.screen.query_one("#text2", Input).value = "SALMIK"
        await pilot.pause()
        # Move to step 2 (color).
        app.screen.action_next()
        await pilot.pause()
        from welchost.tui.widgets import ColorField

        app.screen.query_one("#solid-0", ColorField).set_value("red")
        app.screen.query_one("#solid-1", ColorField).set_value("blue")
        await pilot.pause()
        assert app.model.banner.rows[0].solid.value == "red"
        assert app.model.banner.rows[1].solid.value == "blue"


async def test_row2_color_group_hidden_with_one_row(fake_home):
    detect.DEV_MODE = True
    app = WelchostApp()
    async with app.run_test() as pilot:
        await app.push_screen(Wizard())
        await pilot.pause()
        app.screen.action_next()  # step 2 with a single row
        await pilot.pause()
        assert app.screen.query_one("#row-1-group").display is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_wizard_rows.py -q`
Expected: FAIL — `NoMatches: #solid-0` (step 2 still uses single-row ids `#solid`/`#grad_start`).

- [ ] **Step 3: Rewrite step 2 for per-row color**

Replace the body of `src/welchost/tui/screens/step_color.py` with:

```python
"""Wizard step 2 — per-row color mode + reusable color pickers (keyboard only)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, RadioButton, RadioSet, Select

from ..widgets import ColorField, apply_visibility

DIRECTIONS = ["horizontal", "vertical", "diagonal"]


class StepColor(Vertical):
    """Edits each row's color_mode and solid/gradient colors via ColorField."""

    title = "step 2 · color"

    def compose(self) -> ComposeResult:
        # Two fixed row groups (the UI caps the banner at two rows); the second is
        # hidden unless the model actually has a second row.
        for idx in (0, 1):
            with Vertical(id=f"row-{idx}-group", classes="row-color-group"):
                yield Label(f"row {idx + 1}", classes="section-label")
                with RadioSet(id=f"mode-{idx}"):
                    yield RadioButton("solid", id=f"mode-solid-{idx}")
                    yield RadioButton("gradient", id=f"mode-gradient-{idx}")
                with Vertical(id=f"solid-box-{idx}"):
                    yield ColorField("color", self._row_value(idx, "solid"), id=f"solid-{idx}")
                with Vertical(id=f"grad-box-{idx}"):
                    yield ColorField(
                        "gradient start", self._row_value(idx, "grad_start"), id=f"grad_start-{idx}"
                    )
                    yield ColorField(
                        "gradient end", self._row_value(idx, "grad_end"), id=f"grad_end-{idx}"
                    )
                    yield Label("direction", classes="section-label")
                    yield Select(
                        [(d, d) for d in DIRECTIONS],
                        id=f"grad_dir-{idx}",
                        value=self._row_value(idx, "grad_dir"),
                        allow_blank=False,
                    )

    # --- model helpers -------------------------------------------------------

    def _row(self, idx: int):
        rows = self.app.model.banner.rows
        return rows[idx] if idx < len(rows) else None

    def _row_value(self, idx: int, key: str) -> str:
        row = self._row(idx)
        if row is None:
            row = self.app.model.banner.rows[0]  # placeholder values for the hidden group
        return {
            "solid": row.solid.value,
            "grad_start": row.gradient.start,
            "grad_end": row.gradient.end,
            "grad_dir": row.gradient.direction,
        }[key]

    @staticmethod
    def _suffix(widget_id: str) -> int:
        return int(widget_id.rsplit("-", 1)[1])

    def load_from_model(self) -> None:
        rows = self.app.model.banner.rows
        for idx in (0, 1):
            present = idx < len(rows)
            apply_visibility(self, {f"row-{idx}-group": present})
            if not present:
                continue
            row = rows[idx]
            is_grad = row.color_mode == "gradient"
            self.query_one(
                f"#mode-gradient-{idx}" if is_grad else f"#mode-solid-{idx}", RadioButton
            ).value = True
            self.query_one(f"#solid-{idx}", ColorField).set_value(row.solid.value)
            self.query_one(f"#grad_start-{idx}", ColorField).set_value(row.gradient.start)
            self.query_one(f"#grad_end-{idx}", ColorField).set_value(row.gradient.end)
            self.query_one(f"#grad_dir-{idx}", Select).value = row.gradient.direction
            self._toggle(idx, is_grad)

    def _toggle(self, idx: int, is_grad: bool) -> None:
        apply_visibility(
            self, {f"solid-box-{idx}": not is_grad, f"grad-box-{idx}": is_grad}
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id and event.radio_set.id.startswith("mode-"):
            idx = self._suffix(event.radio_set.id)
            row = self._row(idx)
            if row is None:
                return
            is_grad = event.radio_set.pressed_index == 1
            row.color_mode = "gradient" if is_grad else "solid"
            self._toggle(idx, is_grad)
            self.app.refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id and event.select.id.startswith("grad_dir-") and event.value is not None:
            row = self._row(self._suffix(event.select.id))
            if row is not None:
                row.gradient.direction = str(event.value)
                self.app.refresh_preview()

    def on_color_field_changed(self, event: ColorField.Changed) -> None:
        fid = event.field.id or ""
        idx = self._suffix(fid)
        row = self._row(idx)
        if row is None:
            return
        if fid.startswith("solid-"):
            row.solid.value = event.value or "cyan"
        elif fid.startswith("grad_start-"):
            row.gradient.start = event.value or "cyan"
        elif fid.startswith("grad_end-"):
            row.gradient.end = event.value or "magenta"
        self.app.refresh_preview()
```

Add a CSS rule so the row groups grow to content. In `src/welchost/tui/screens/wizard.py`, inside the `CSS` string, add a line after the `Wizard #steps Vertical { height: auto; }` rule:

```css
    Wizard .row-color-group { height: auto; padding: 0 0 1 0; }
```

- [ ] **Step 4: Run wizard tests to verify they pass**

Run: `pytest tests/test_wizard_rows.py -q`
Expected: PASS (all four tests).

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

Run: `ruff check src tests && ruff format --check src tests`

```bash
git add src/welchost/tui/screens/step_color.py src/welchost/tui/screens/wizard.py tests/test_wizard_rows.py
git commit -m "feat(tui): per-row color controls in wizard step 2"
```

---

## Task 6: Remove temporary shims and verify no stragglers

**Files:**
- Modify: `src/welchost/config.py` (remove shims)
- Possibly modify: any straggler found by grep
- Test: full suite + manual preview

**Interfaces:**
- Removes: `Banner.text`, `Banner.color_mode`, `WelchostConfig.solid`, `WelchostConfig.gradient` shim properties.

- [ ] **Step 1: Grep for any remaining use of the flat attributes**

Run:
```bash
grep -rn -E '\.banner\.text|\.banner\.color_mode|\bcfg\.solid|\bcfg\.gradient|\.model\.solid|\.model\.gradient|config\.solid|config\.gradient' src tests
```
Expected after Tasks 1–5: only matches inside `src/welchost/config.py` (the shim definitions themselves). Any match elsewhere is a straggler — migrate it to the `rows` API before continuing (e.g. `x.banner.text` → `x.banner.rows[0].text`). Note: `build_figlet(cfg)` in `generator.py` calls `_render_figlet(config.banner.font, config.banner.text)`; change its `config.banner.text` to `config.banner.rows[0].text`.

- [ ] **Step 2: Update `build_figlet` to drop the shim**

In `src/welchost/generator.py`, replace the body of `build_figlet`:

```python
def build_figlet(config: WelchostConfig) -> str:
    """Render the first banner row to ASCII art at the font's native size.

    Falls back to the ``standard`` font if the configured font is missing.
    """
    return _render_figlet(config.banner.font, config.banner.rows[0].text)
```

- [ ] **Step 3: Remove the shim properties from `config.py`**

Delete the four shim properties added in Task 1: `Banner.text`, `Banner.text.setter`, `Banner.color_mode`, `Banner.color_mode.setter` (and the comment block), and `WelchostConfig.solid`, `WelchostConfig.gradient` (and their comment block).

- [ ] **Step 4: Remove the shim-specific test**

In `tests/test_config.py`, delete `test_compat_shims_proxy_first_row` (it asserts behavior we just removed).

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS. A failure here means a straggler still relied on a shim — fix it to use `rows` and re-run.

- [ ] **Step 6: Manual WYSIWYG smoke check (preview == generated)**

Run a two-row banner through both renderers in dev mode and eyeball that they match:

```bash
python -c "
from welchost.config import WelchostConfig, Row, SolidColor, GradientColor
from welchost.render import render_banner
from welchost.generator import render_welcome_banner
from rich.console import Console
cfg = WelchostConfig.default()
cfg.banner.font = 'ansi_shadow'
cfg.banner.rows = [
    Row(text='JAKUB', color_mode='solid', solid=SolidColor(value='#d97757')),
    Row(text='SALMIK', color_mode='gradient', gradient=GradientColor(start='cyan', end='magenta')),
]
Console().print(render_banner(cfg))
src = render_welcome_banner(cfg)
ns = {'__name__': 'not_main'}
exec(compile(src, 'welcome_banner.py', 'exec'), ns)
print('--- generated ---')
ns['render']()
"
```
Expected: two stacked rows ("JAKUB" terracotta, "SALMIK" cyan→magenta) appear from BOTH the Rich preview and the generated renderer, visually matching (same shape, same colors).

- [ ] **Step 7: Run the wizard end-to-end in dev mode (optional manual)**

Run: `welchost --dev config`
Expected: step 1 shows a "second row" input; entering a second row makes step 2 show two color groups; the live preview stacks both rows; `ctrl+s` saves and the generated banner matches the preview. Quit with `q`.

- [ ] **Step 8: Lint and final commit**

Run: `ruff check src tests && ruff format --check src tests && pytest -q`
Expected: all clean/green.

```bash
git add src/welchost/config.py src/welchost/generator.py tests/test_config.py
git commit -m "refactor(config): drop temporary single-row compatibility shims"
```

---

## Self-Review (completed during planning)

**Spec coverage (Phase 1 scope):**
- Rows data model + migration → Task 1. ✓
- Multi-row render in both renderers → Tasks 2 (`render.py`) and 3 (template). ✓
- Per-row color → Tasks 1 (model), 2/3 (render/generate), 5 (wizard). ✓
- Wizard steps 1–2 → Tasks 4 (step 1) and 5 (step 2). ✓
- Theme migration to rows model → Task 1 (Step 5–6). ✓
- WYSIWYG parity preserved → identical math in `render.py` and template; verified in Task 6 Step 6. ✓
- Lossless round-trip + legacy migration → Task 1 tests. ✓
- `fit_width` field added to schema (used by Phase 2) → Task 1. ✓
- Out of Phase 1 (deferred): `SAFE_FONTS`, design-time fit indicator/auto-fit, styled metadata (Phase 2); runtime compact fallback (Phase 3). Metadata stays the existing plain `info_lines`.

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every test step shows the assertion and the expected pass/fail.

**Type consistency:** `Row(text, color_mode, solid, gradient)`, `Banner(font, align, fit_width, rows)`, `WelchostConfig(banner, decoration, ornament, info, meta)` used consistently across tasks. Generator row dict keys (`art`, `color_mode`, `solid`, `grad_start`, `grad_end`, `grad_dir`) match the template's `colorize_block`/`build_rows` reads. Wizard control ids are suffixed `-{idx}` consistently and parsed by `_suffix`. `_render_figlet(font, text)` (existing in `generator.py`) is reused by `render.py` Task 2 and `generator.py` Task 3.
