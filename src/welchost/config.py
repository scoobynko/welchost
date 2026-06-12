"""welchost.toml read/write and the WelchostConfig dataclass.

The dataclass mirrors the TOML schema exactly and round-trips losslessly. All
paths come from :mod:`welchost.detect` — never hardcode them.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import tomli_w

from . import detect

SCHEMA_VERSION = "1.0.0"

VALID_SIZES = ("auto", "sm", "md", "lg", "xl")
VALID_COLOR_MODES = ("solid", "gradient")
VALID_BORDER_STYLES = ("panel", "box", "double", "rounded", "ascii", "none")


@dataclass
class Banner:
    text: str = "Welcome"
    font: str = "slant"
    size: str = "auto"
    color_mode: str = "solid"


@dataclass
class SolidColor:
    value: str = "cyan"


@dataclass
class GradientColor:
    start: str = "cyan"
    end: str = "magenta"


@dataclass
class Decoration:
    border_style: str = "panel"
    border_color: str = "magenta"


@dataclass
class Info:
    show_user: bool = True
    show_host: bool = True
    show_os: bool = True
    show_datetime: bool = True
    show_uptime: bool = False
    show_shell: bool = False
    show_python: bool = False
    show_ip: bool = False


@dataclass
class Meta:
    welchost_version: str = SCHEMA_VERSION
    created_at: str = ""


@dataclass
class WelchostConfig:
    """In-memory representation of welchost.toml."""

    banner: Banner = field(default_factory=Banner)
    solid: SolidColor = field(default_factory=SolidColor)
    gradient: GradientColor = field(default_factory=GradientColor)
    decoration: Decoration = field(default_factory=Decoration)
    info: Info = field(default_factory=Info)
    meta: Meta = field(default_factory=Meta)

    @classmethod
    def default(cls) -> WelchostConfig:
        return cls()

    # -- (de)serialization -------------------------------------------------

    def to_toml_dict(self) -> dict:
        """Build the nested dict matching the TOML layout."""
        return {
            "banner": asdict(self.banner),
            "color": {
                "solid": asdict(self.solid),
                "gradient": asdict(self.gradient),
            },
            "decoration": asdict(self.decoration),
            "info": asdict(self.info),
            "meta": asdict(self.meta),
        }

    @classmethod
    def from_toml_dict(cls, data: dict) -> WelchostConfig:
        banner = {**asdict(Banner()), **data.get("banner", {})}
        color = data.get("color", {})
        solid = {**asdict(SolidColor()), **color.get("solid", {})}
        gradient = {**asdict(GradientColor()), **color.get("gradient", {})}
        decoration = {**asdict(Decoration()), **data.get("decoration", {})}
        info = {**asdict(Info()), **data.get("info", {})}
        meta = {**asdict(Meta()), **data.get("meta", {})}
        return cls(
            banner=Banner(**banner),
            solid=SolidColor(**solid),
            gradient=GradientColor(**gradient),
            decoration=Decoration(**decoration),
            info=Info(**info),
            meta=Meta(**meta),
        )


def load_config(path: Path | None = None) -> WelchostConfig | None:
    """Load welchost.toml, or return None if it does not exist."""
    path = path or detect.get_config_path()
    if not path.exists():
        return None
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return WelchostConfig.from_toml_dict(data)


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
