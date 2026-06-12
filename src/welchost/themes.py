"""The 12 built-in themes.

Each theme is plain data that converts to a full :class:`WelchostConfig`. No I/O.
Font names here must all be valid pyfiglet fonts (enforced by test_themes.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    Banner,
    Decoration,
    GradientColor,
    Info,
    SolidColor,
    WelchostConfig,
)


@dataclass(frozen=True)
class Theme:
    name: str
    font: str
    border_style: str
    border_color: str
    # solid color OR gradient (start/end). If gradient is set, color_mode=gradient.
    color: str | None = None
    gradient_start: str | None = None
    gradient_end: str | None = None

    @property
    def is_gradient(self) -> bool:
        return self.gradient_start is not None

    @property
    def swatch(self) -> str:
        """Representative color for gallery previews."""
        return self.gradient_start or self.color or "white"

    def to_config(self, text: str = "Welcome") -> WelchostConfig:
        color_mode = "gradient" if self.is_gradient else "solid"
        solid = SolidColor(value=self.color or "cyan")
        gradient = GradientColor(
            start=self.gradient_start or "cyan",
            end=self.gradient_end or "magenta",
        )
        return WelchostConfig(
            banner=Banner(text=text, font=self.font, size="auto", color_mode=color_mode),
            solid=solid,
            gradient=gradient,
            decoration=Decoration(border_style=self.border_style, border_color=self.border_color),
            info=Info(),
        )


THEMES: dict[str, Theme] = {
    t.name: t
    for t in [
        Theme("ghost", "slant", "panel", "magenta", color="cyan"),
        Theme("hacker", "doom", "box", "green", color="green"),
        Theme("dracula", "standard", "rounded", "#f38ba8", color="#cba6f7"),
        Theme("catppuccin", "big", "panel", "#89dceb", color="#cba6f7"),
        Theme("nord", "thin", "panel", "#8fbcbb", color="#88c0d0"),
        Theme("gruvbox", "banner", "box", "#fabd2f", color="#fe8019"),
        Theme("tokyo-night", "nancyj", "panel", "#7aa2f7", color="#bb9af7"),
        Theme("monochrome", "larry3d", "double", "white", color="white"),
        Theme("hot", "epic", "box", "yellow", color="red"),
        Theme("ocean", "univers", "rounded", "#00ccff", color="#0099ff"),
        Theme("matrix", "banner", "none", "green", color="bright_green"),
        Theme(
            "sunset",
            "slant",
            "panel",
            "#ff6b35",
            gradient_start="#ff6b35",
            gradient_end="#f7c59f",
        ),
    ]
}


def get_theme(name: str) -> Theme | None:
    return THEMES.get(name)


def all_themes() -> list[Theme]:
    return list(THEMES.values())
