"""welchost.toml read/write and the WelchostConfig dataclass.

The dataclass mirrors the TOML schema exactly and round-trips losslessly. All
paths come from :mod:`welchost.detect` — never hardcode them.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path

import tomli_w

from . import detect

SCHEMA_VERSION = "2.0.0"

VALID_ALIGN = ("left", "center", "right")
VALID_COLOR_MODES = ("solid", "gradient")
VALID_GRADIENT_DIRECTIONS = ("horizontal", "vertical", "diagonal")
VALID_BORDER_STYLES = ("panel", "box", "double", "rounded", "ascii", "none")
VALID_INFO_LAYOUTS = ("inline", "stacked")


@dataclass
class SolidColor:
    value: str = "cyan"


@dataclass
class GradientColor:
    start: str = "cyan"
    end: str = "magenta"
    # How the blend runs across the art block: horizontal (left→right per line),
    # vertical (top→bottom), or diagonal (top-left→bottom-right).
    direction: str = "horizontal"


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


@dataclass
class Decoration:
    # Custom builds (no template) start borderless; templates set their own.
    border_style: str = "none"
    border_color: str = "magenta"


@dataclass
class Ornament:
    # Predefined flanking ASCII ornaments; see welchost.ornaments. "none" = off.
    name: str = "none"


@dataclass
class Info:
    # Default to a clean two-line footer; the rest stay available for TOML power
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


@dataclass
class Meta:
    welchost_version: str = SCHEMA_VERSION
    created_at: str = ""


def _build(cls, data: dict):
    """Construct a config dataclass, ignoring keys it no longer defines.

    Lets older welchost.toml files (e.g. with the removed ``size`` key) load
    without crashing.
    """
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


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


def load_config(path: Path | None = None) -> WelchostConfig | None:
    """Load welchost.toml, or return None if it is absent, unreadable, or invalid.

    A hand-edited config with broken TOML must never crash the tool — the TUI
    reads this at startup and ``preview``/``doctor`` read it too. On a parse or
    read error we treat it as "no usable config" (None) so the app still opens
    and the user can rebuild; the file itself is left untouched.
    """
    path = path or detect.get_config_path()
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        return WelchostConfig.from_toml_dict(data)
    except (tomllib.TOMLDecodeError, OSError, TypeError, ValueError):
        return None


def save_config(config: WelchostConfig, path: Path | None = None) -> Path:
    """Write welchost.toml, creating the config dir and stamping created_at."""
    path = path or detect.get_config_path()
    detect.ensure_config_dir()
    if not config.meta.created_at:
        config.meta.created_at = datetime.now(UTC).isoformat(timespec="seconds")
    config.meta.welchost_version = SCHEMA_VERSION
    with path.open("wb") as fh:
        tomli_w.dump(config.to_toml_dict(), fh)
    return path


def config_exists(path: Path | None = None) -> bool:
    return (path or detect.get_config_path()).exists()
