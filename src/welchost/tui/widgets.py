"""Shared TUI widgets."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.widgets import Static

from ..config import WelchostConfig
from ..render import render_banner


class BannerPreview(Static):
    """Live banner preview. Re-renders instantly when `show()` is called."""

    DEFAULT_CSS = """
    BannerPreview {
        border: round $panel;
        padding: 0 1;
        height: auto;
        min-height: 6;
        overflow-x: auto;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cfg: WelchostConfig | None = None

    def show(self, cfg: WelchostConfig) -> None:
        self._cfg = cfg
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        if self._cfg is None:
            return Text("")
        try:
            return render_banner(self._cfg)
        except Exception as exc:  # never crash the UI on a bad font/color
            return Text(f"preview error: {exc}", style="red")
