"""Export the Welchost splash logo (pixel-art ghost + wordmark) to PNG / GIF.

The logo is generated at runtime by ``welchost.tui.logo`` as a Rich ``Text`` grid
of block glyphs in the terracotta accent. Rather than rasterize those glyphs with
a font (which never matches a terminal's tall 1:2 cells), this script decomposes
each block character into the *pixels it represents* on a 1-wide x 2-tall sub-cell
grid, then scales it up. That reproduces the terminal exactly and makes animation
free: each animation frame is just another grid to decompose.

Glyph -> (top sub-pixel, bottom sub-pixel):
    ' ' -> background          '█' -> accent, accent
    '▀' -> accent, background   '▄' -> background, accent
    '░' '▒' -> shade, shade    (the double_blocky two-tone seen in the TUI)

Requires Pillow (dev-only tool, not a project dependency):  pip install Pillow

Usage:
    python scripts/export_logo.py [OUT.png]            # static, frame 0
    python scripts/export_logo.py OUT.gif --gif        # animated splash
    python scripts/export_logo.py ... --scale 14 --bg "#1a1a1a" --frames-dir DIR
    python scripts/export_logo.py ... --bg transparent # PNG only (GIF needs solid)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

# Make src/ importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from welchost.themes import ACCENT  # noqa: E402
from welchost.tui.logo import _FRAMES, _ghost_frame, _wordmark  # noqa: E402

DEFAULT_BG = "#1a1a1a"  # Ghostty-ish dark, so the ░ shade reads with depth (Image #2)
SHADE_DARKEN = 0.62  # the two-tone (░) base = accent darkened toward black by this factor


def hex_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def blend(bg: tuple[int, int, int], fg: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(b + (f - b) * t) for b, f in zip(bg, fg, strict=True))  # type: ignore[return-value]


def frame_lines(frame: int) -> list[str]:
    """Ghost beside the wordmark for one animation frame — the same composition as
    ``logo_text`` minus the shell-prompt/tagline chrome. The ghost floats inside a
    fixed-size lane, so every frame has identical dimensions (required for a GIF)."""
    word = _wordmark()
    ghost = _ghost_frame(frame)
    gw = max((len(g) for g in ghost), default=0)
    total = max(len(ghost), len(word))
    g_off = (total - len(ghost)) // 2
    w_off = (total - len(word)) // 2

    rows: list[str] = []
    for i in range(total):
        gi, wi = i - g_off, i - w_off
        g = ghost[gi] if 0 <= gi < len(ghost) else ""
        w = word[wi] if 0 <= wi < len(word) else ""
        rows.append(g.ljust(gw) + "   " + w)
    width = max((len(r) for r in rows), default=0)
    return [r.ljust(width) for r in rows]


def render_frame(
    rows: list[str],
    scale: int,
    padding: int,
    bg: tuple[int, int, int] | None,
    accent: tuple[int, int, int],
    shade: tuple[int, int, int, int],
) -> Image.Image:
    """Decompose block glyphs to a sub-pixel grid and scale up with nearest-neighbor
    so the pixels stay crisp (no anti-alias blur). ``shade`` is RGBA so the two-tone
    cells can be a lower-opacity accent that adapts to whatever sits behind them."""
    transparent = bg is None
    fill_bg = (0, 0, 0, 0) if transparent else (*bg, 255)
    a, s = (*accent, 255), shade

    cols = max((len(r) for r in rows), default=0)
    grid_w, grid_h = cols, len(rows) * 2  # each char row = 2 stacked sub-pixels
    img = Image.new("RGBA", (grid_w, grid_h), fill_bg)
    px = img.load()

    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "█":
                top = bot = a
            elif ch == "▀":
                top, bot = a, fill_bg
            elif ch == "▄":
                top, bot = fill_bg, a
            elif ch in "░▒":
                top = bot = s
            elif ch == " ":
                continue
            else:  # ▓ or any unexpected dense glyph
                top = bot = a
            px[c, r * 2] = top
            px[c, r * 2 + 1] = bot

    img = img.resize((grid_w * scale, grid_h * scale), Image.NEAREST)
    if padding:
        canvas = Image.new("RGBA", (img.width + 2 * padding, img.height + 2 * padding), fill_bg)
        canvas.alpha_composite(img, (padding, padding))
        img = canvas
    return img


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def render_svg(
    rows: list[str],
    scale: int,
    padding: int,
    bg: tuple[int, int, int] | None,
    accent: tuple[int, int, int],
    shade: tuple[int, int, int],
    opacity: float,
) -> str:
    """Emit the (static) logo as SVG: each block glyph becomes <rect>s on a 1x2
    sub-cell grid. The two-tone cells use the darkened ``shade`` color at ``opacity``
    (real vector alpha), so the SVG adapts to any background. Horizontally-adjacent
    same-kind cells merge into one rect (run-length) to keep the file small."""
    a, sh = _hex(accent), _hex(shade)
    cols = max((len(r) for r in rows), default=0)

    # sub[y][x] = "A" (accent) | "S" (shade) | None (empty); each char row = 2 sub-rows.
    sub: list[list[str | None]] = []
    for line in rows:
        top: list[str | None] = []
        bot: list[str | None] = []
        for ch in line.ljust(cols):
            if ch == "█":
                t, b = "A", "A"
            elif ch == "▀":
                t, b = "A", None
            elif ch == "▄":
                t, b = None, "A"
            elif ch in "░▒":
                t, b = "S", "S"
            elif ch == " ":
                t, b = None, None
            else:
                t, b = "A", "A"
            top.append(t)
            bot.append(b)
        sub.append(top)
        sub.append(bot)

    rects: list[str] = []
    for y, srow in enumerate(sub):
        x = 0
        while x < cols:
            kind = srow[x]
            if kind is None:
                x += 1
                continue
            run = 1
            while x + run < cols and srow[x + run] == kind:
                run += 1
            fill = a if kind == "A" else sh
            op = "" if kind == "A" else f' fill-opacity="{opacity:g}"'
            rects.append(
                f'<rect x="{padding + x * scale}" y="{padding + y * scale}" '
                f'width="{run * scale}" height="{scale}" fill="{fill}"{op}/>'
            )
            x += run

    width = cols * scale + 2 * padding
    height = len(sub) * scale + 2 * padding
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" shape-rendering="crispEdges">'
    )
    body = f'<rect width="{width}" height="{height}" fill="{_hex(bg)}"/>' if bg else ""
    return head + body + "".join(rects) + "</svg>\n"


def _to_indexed(
    frame: Image.Image, accent: tuple[int, int, int], shade: tuple[int, int, int]
) -> Image.Image:
    """Map a flat-colored RGBA frame to a P-mode image whose palette index 0 is the
    transparent background. Works only because every pixel is exactly transparent,
    accent, or shade — so a 3-entry palette is lossless (no quantization)."""
    w, h = frame.size
    src = frame.load()
    out = Image.new("P", (w, h), 0)
    dst = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, al = src[x, y]
            if al == 0:
                dst[x, y] = 0
            elif (r, g, b) == accent:
                dst[x, y] = 1
            else:
                dst[x, y] = 2
    out.putpalette([255, 0, 255, *accent, *shade])  # index 0 is the transparent slot
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "output", nargs="?", help="output path (default: ~/Downloads/welchost-logo.{png,gif})"
    )
    ap.add_argument(
        "--gif", action="store_true", help="render the animated splash instead of a still"
    )
    ap.add_argument("--scale", type=int, default=14, help="pixels per sub-cell (default: 14)")
    ap.add_argument("--padding", type=int, default=28, help="margin in px (default: 28)")
    ap.add_argument(
        "--bg", default=DEFAULT_BG, help='background hex or "transparent" (default: #1a1a1a)'
    )
    ap.add_argument(
        "--shade",
        type=float,
        default=0.8,
        help="opacity of the darkened two-tone (░) cells, 0..1 (1.0 = opaque; default: 0.8)",
    )
    ap.add_argument(
        "--duration", type=int, default=500, help="ms per GIF frame (default: 500, matches the TUI)"
    )
    ap.add_argument("--frames-dir", help="also write each GIF frame as a PNG into this dir")
    ap.add_argument("--svg", action="store_true", help="render a static vector SVG (frame 0)")
    args = ap.parse_args()

    transparent = args.bg.lower() == "transparent"
    bg = None if transparent else hex_rgb(args.bg)
    accent = hex_rgb(ACCENT)
    alpha = max(0.0, min(1.0, args.shade))

    # The two-tone cells are a darkened accent at `alpha`. PNG/SVG carry real alpha so
    # they adapt to any background (deeper on dark, softer on white); GIF has no partial
    # alpha, so its shade is baked toward white (the page color on PyPI).
    shade_color = blend((0, 0, 0), accent, SHADE_DARKEN)
    if bg is None:  # transparent
        shade_rgba = (*shade_color, round(255 * alpha))
        shade_solid = blend((255, 255, 255), shade_color, alpha)
    else:
        shade_rgba = (*blend(bg, shade_color, alpha), 255)
        shade_solid = blend(bg, shade_color, alpha)

    svg = args.svg or (args.output is not None and args.output.lower().endswith(".svg"))
    default_name = (
        "welchost-logo.svg" if svg else "welchost-logo.gif" if args.gif else "welchost-logo.png"
    )
    out = Path(args.output) if args.output else Path.home() / "Downloads" / default_name
    out.parent.mkdir(parents=True, exist_ok=True)

    if svg:
        markup = render_svg(
            frame_lines(0), args.scale, args.padding, bg, accent, shade_color, alpha
        )
        out.write_text(markup)
        print(f"Wrote {out}  ({len(markup)} bytes)")
        return

    if not args.gif:
        img = render_frame(frame_lines(0), args.scale, args.padding, bg, accent, shade_rgba)
        img.save(out)
        print(f"Wrote {out}  ({img.width}x{img.height})")
        return

    frames = [
        render_frame(frame_lines(i), args.scale, args.padding, bg, accent, (*shade_solid, 255))
        for i in range(len(_FRAMES))
    ]
    if args.frames_dir:
        fdir = Path(args.frames_dir)
        fdir.mkdir(parents=True, exist_ok=True)
        for i, fr in enumerate(frames):
            fr.save(fdir / f"frame-{i:02d}.png")
        print(f"Wrote {len(frames)} frames -> {fdir}")

    if transparent:
        # 1-bit transparent GIF: palette index 0 is the transparent slot; disposal=2
        # clears each frame back to transparent so the floating ghost leaves no trail.
        idx = [_to_indexed(f, accent, shade_solid) for f in frames]
        idx[0].save(
            out,
            save_all=True,
            append_images=idx[1:],
            duration=args.duration,
            loop=0,
            transparency=0,
            disposal=2,
            optimize=False,
        )
    else:
        # Solid bg: flatten and quantize to a tight palette.
        flat = [f.convert("RGB").quantize(colors=8, dither=Image.NONE) for f in frames]
        flat[0].save(
            out,
            save_all=True,
            append_images=flat[1:],
            duration=args.duration,
            loop=0,
            optimize=True,
            disposal=2,
        )
    w, h = frames[0].width, frames[0].height
    print(f"Wrote {out}  ({w}x{h}, {len(frames)} frames @ {args.duration}ms)")


if __name__ == "__main__":
    main()
