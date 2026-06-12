"""The built-in templates.

Each template is plain data that converts to a full :class:`WelchostConfig`.
No I/O. Every font name here must be a valid pyfiglet font (enforced by
test_themes.py).
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

# Brand accent (matches the terracotta used on jakubsalmik.com).
ACCENT = "#d97757"


@dataclass(frozen=True)
class Theme:
    name: str
    font: str
    border_style: str
    border_color: str
    blurb: str = ""
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
        Theme("claude", "ansi_shadow", "rounded", ACCENT, "filled · terracotta", color=ACCENT),
        Theme("codex", "ansi_regular", "box", "cyan", "filled · clean", color="white"),
        Theme("ghost", "slant", "panel", "magenta", "the classic", color="cyan"),
        Theme(
            "matrix", "ansi_regular", "none", "green", "filled · borderless", color="bright_green"
        ),
        Theme(
            "sunset",
            "slant",
            "panel",
            "#ff6b35",
            "gradient demo",
            gradient_start="#ff6b35",
            gradient_end="#f7c59f",
        ),
        Theme("mono", "pagga", "none", "white", "compact · minimal", color="white"),
    ]
}


def get_theme(name: str) -> Theme | None:
    return THEMES.get(name)


def all_themes() -> list[Theme]:
    return list(THEMES.values())
