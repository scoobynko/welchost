# Flexible welcome screen — design

**Date:** 2026-06-30
**Status:** Approved (ready for planning)
**Backlog:** Adopts and extends **WH-4 "Better text & layout flexibility"** (Flexibility/Rendering/UX, Effort L, Priority High), plus a new metadata-styling sub-feature not previously in the backlog.

## Summary

Make Welchost banners bigger, stackable, and resize-proof, and make the system-info
metadata visually part of the banner instead of plain debug-style text. Three
threads:

- **A — Stacked two-row banner:** text split across two stacked figlet rows, sharing
  one font, with per-row color/gradient.
- **B — Width safety:** curated "won't-break" font set, design-time fit measurement +
  auto-fit, and a runtime fallback where the generated script steps down to a compact
  variant when the live terminal is too narrow.
- **C — Styled metadata:** a single inline info row that inherits the banner's palette
  (accent labels + banner-colored values) with glyph separators.

Delivered as **one spec in three phases** (see Phasing).

## Goals

- A banner can be one or two stacked rows; each row carries its own color/gradient; both
  rows share the banner font and alignment.
- A user cannot easily build a banner that shatters: bad-rendering fonts are hidden by
  default, overflow is flagged and one-click-fixable before save, and a too-narrow
  terminal at runtime degrades gracefully instead of wrapping into garbage.
- Metadata reads as part of the banner design (inherited colors, inline layout).
- Existing `welchost.toml` files keep working (automatic migration); new configs
  round-trip losslessly.
- WYSIWYG parity between the TUI/CLI preview (`render.py`) and the generated
  `welcome_banner.py` is preserved everywhere.

## Non-goals

- More than two rows in the wizard UI (the data model allows N; the UI caps at 2 for now).
- Animation (that is WH-2, a separate XL backlog item).
- New ornaments/borders (that is WH-3).
- Per-row *fonts* — font is shared across rows by design.

## Constraints to protect (from CLAUDE.md)

- **WYSIWYG parity:** every render change lands in BOTH `render.py` and
  `welcome_banner.py.j2`. Gradient/color math stays identical on both sides.
- **Lossless TOML round-trip.**
- **Core stays Textual-free**; `tui/` depends on core, never the reverse.
- **`.zshrc` sentinel idempotency** and **DEV isolation** must not regress.
- Generated `welcome_banner.py` must not require third-party imports beyond Rich, and
  must stay fast/non-blocking on shell open.

## Section 1 — Data model & migration

`[banner]` changes from a single text+color to a **list of rows**. Font and alignment
stay shared at the banner level; color moves per-row. New `fit_width` target.

```toml
[banner]
font = "ansi_shadow"        # shared across rows
align = "left"              # left | center | right
fit_width = 80              # target width for fit checks (0 = disabled)

[[banner.rows]]
text = "JAKUB"
color_mode = "solid"        # solid | gradient
[banner.rows.solid]
value = "#d97757"

[[banner.rows]]
text = "SALMIK"
color_mode = "gradient"
[banner.rows.gradient]
start = "cyan"
end = "magenta"
direction = "horizontal"    # horizontal | vertical | diagonal
```

### Dataclasses (`config.py`)

- New `Row`: `text: str`, `color_mode: str = "solid"`, `solid: SolidColor`,
  `gradient: GradientColor`.
- `Banner`: `font: str`, `align: str`, `fit_width: int = 80`, `rows: list[Row]`.
- The old top-level `[color.solid]` / `[color.gradient]` tables are removed from the
  *new* schema (color now lives inside each row) but are still **read** for migration.
- `SCHEMA_VERSION` bumps to `2.0.0`.

### Migration (`from_toml_dict`)

If a loaded config has no `banner.rows` but has the legacy `banner.text`, build a single
`Row` from `banner.text` + legacy `banner.color_mode` + legacy top-level
`[color.solid]` / `[color.gradient]`. Result: old 1-line banners load unchanged as a
1-row banner. Keep the existing `_build()` tolerance for unknown keys. A config that
fails to parse still returns `None` (unchanged behavior).

### Round-trip

`to_toml_dict` emits `[[banner.rows]]` array-of-tables with each row's own
`solid`/`gradient` subtable. New configs round-trip losslessly; covered by
`test_config.py`.

## Section 2 — Rendering pipeline (WYSIWYG parity)

### `render.py`

`render_art` renders a **stack of row-blocks** instead of one block:

1. For each row: render `row.text` with the shared `banner.font` via `_render_figlet`,
   strip blank edges, then color it with the existing `_art_rows` logic using *that
   row's* `color_mode` + solid/gradient. Each row's gradient is computed within its own
   block (self-contained blend — predictable, no cross-row bleed).
2. Stack the row-blocks vertically (one blank line between rows; spacing fixed for now).
3. `_flank` wraps the **whole stacked block** with the ornament (ornament flanks the
   full banner, not each row); current centering/offset behavior preserved.

`_art_rows`, `_blend`, `_gradient_factor`, `_strip_blank_edges` are reused per-row
unchanged. `_art_rows` is refactored to take an explicit `(color_mode, solid, gradient)`
rather than reading them off `cfg` globally.

### Generated template (`welcome_banner.py.j2` + `generator.py`)

The generator passes a `rows` list; each entry carries `{art_lines (baked json),
color_mode, solid_rgb, grad_start_rgb, grad_end_rgb, grad_direction}`. The template
loops over rows, applying the same pure-Python ANSI per-row coloring already inlined
today, and stacks them with the same blank-line spacing. The single-art scalars
(`art_json`, `solid_rgb`, `grad_*`) are replaced by the per-row list. Enum clamping
(`_enum`) is applied per row.

## Section 3 — Width safety

### Layer 1 — Curated "won't-break" font set (`fonts.py`)

New `SAFE_FONTS`: a vetted subset of `CURATED` that renders cleanly (no missing/garbled
glyphs, predictable per-character width). The wizard font picker shows `SAFE_FONTS` by
default with a "show all fonts" toggle (all pyfiglet fonts remain reachable). A new
`test_fonts.py` renders every safe font across the needed charset (A–Z, a–z, 0–9, space,
common punctuation) and asserts non-empty, non-degenerate output.

### Layer 2 — Design-time fit (wizard)

A helper measures the rendered art's widest line (across both rows, including ornament
flanking) and compares it to `banner.fit_width`. When it overflows:

- the preview shows a width indicator, e.g. `width 94 / 80 ⚠`;
- an **auto-fit** action picks the largest `SAFE_FONTS` entry whose render of the current
  text fits within `fit_width`, and applies it.

Stacking inherently reduces width (two short rows ≪ one long line), so this composes with
Section 1.

### Layer 3 — Runtime fallback (Phase 3)

The generator bakes a **second "compact" variant** alongside the primary: same
text/colors rendered in an **auto-derived** next-smaller `SAFE_FONTS` font (no extra
config). The generated `welcome_banner.py` checks `shutil.get_terminal_size().columns`
on each shell open and prints:

- the **full** banner if its width fits the terminal,
- the **compact** variant if the window is narrower,
- a **plain-text styled title** floor if even compact won't fit.

This is the only added runtime logic in the generated script: a width read + a pick, no
new imports. Both variants are rendered in preview so the fallback stays WYSIWYG-tested.

## Section 4 — Styled metadata

Replace `info_text()`'s plain stacked `dim` `key: value` lines with a styled inline row
that inherits the banner palette.

- **Labels/icons:** accent color = `decoration.border_color` if a border is set, else the
  banner color (`gradient.start` / `solid.value` of the first row). Overridable via
  `info.accent`.
- **Values:** banner color, slightly dimmed, so the big art still dominates.
- **Separator:** configurable glyph, default `·`.
- **Layout:** single inline row, aligned under the banner per `banner.align`. If the row
  itself exceeds `fit_width`, wrap to a second inline line at a separator boundary (never
  mid-item).

### Config additions (`[info]`)

```toml
[info]
# existing toggles unchanged (show_user, show_datetime, show_host, ...)
layout = "inline"        # inline | stacked  (stacked = legacy behavior)
separator = "·"
accent = "auto"          # auto (inherit) | a Rich color name / hex
```

Defaults yield the inline inherited look out of the box; `layout = "stacked"` preserves
the old style for power users. The same styling logic is ported into
`welcome_banner.py.j2` for runtime parity.

## Section 5 — Wizard/UX

Stays 4 steps; per-row color folds color into the rows:

1. **Rows & font** — Row 1 text, optional Row 2 (add/remove), shared safe-font picker
   (+ "show all" toggle), alignment, live width indicator + auto-fit. Live preview.
2. **Colors** — per-row color: mode (solid/gradient) + color/gradient/direction per row.
3. **Decoration & metadata** — border, border color, ornament, info toggles, + metadata
   `layout`/`separator`/`accent` controls.
4. **Confirm** — full preview, fit-check summary (warns if still overflowing), file diff,
   save & install.

The **edit menu** maps to the same steps. The **6 built-in themes** are migrated to the
rows model (each becomes a 1-row banner) so they keep working visually unchanged;
`test_themes.py` continues to validate every theme + font.

## Phasing

| Phase | Delivers | Primary files |
|-------|----------|---------------|
| **1** | Rows data model + migration; multi-row render in both renderers; per-row color; wizard steps 1–2; theme migration | `config.py`, `render.py`, `generator.py`, `templates/welcome_banner.py.j2`, `tui/screens/wizard.py`, `step_text_font.py`, `step_color.py`, `themes.py` |
| **2** | `SAFE_FONTS` + picker default + "show all"; design-time fit indicator + auto-fit; styled inline metadata | `fonts.py`, `step_text_font.py`, `step_decoration.py`, `render.py`, template, `config.py` (`[info]`) |
| **3** | Runtime-responsive: auto-derived compact variant baked + terminal-width fallback in generated script | `generator.py`, `templates/welcome_banner.py.j2` |

## Testing

Protect existing invariants (lossless round-trip, WYSIWYG parity, sentinel idempotency,
DEV isolation) and add:

- `test_config.py`: rows round-trip; **legacy → rows migration**; defaults.
- `test_fonts.py` (new): every `SAFE_FONTS` font renders cleanly across the charset.
- Fit measurement unit tests (width calc incl. ornament flanking; auto-fit picks a
  fitting font).
- Metadata inline-render parity: `render.py` output vs the generated-script string for
  the same config.
- `test_themes.py`: themes still load + render after migration to the rows model.
- Phase 3: generated-script width-fallback logic (full / compact / plain floor) at
  representative terminal widths.

## Open questions / future

- Row spacing is fixed (0/1 blank line) for now; could become configurable later.
- N>2 rows in the UI is deliberately deferred.
- Style randomizer (WH-1) could later target the rows model directly.
