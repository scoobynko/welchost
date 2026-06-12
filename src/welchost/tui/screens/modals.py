"""Reusable modal dialogs."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ...themes import ACCENT


class ConfirmModal(ModalScreen[bool]):
    """A yes/no confirmation overlay, keyboard-driven.

    Two choices rendered on one line; the selected one is shown as ``[ label ]``
    in the accent color, the other dimmed. ``←/→`` (or tab) move the selection,
    ``enter`` activates it, ``y``/``n``/``esc`` are shortcuts. Dismisses with
    True (yes) or False (no) — use via ``app.push_screen(modal, callback)``.
    """

    BINDINGS = [
        ("left", "move(-1)", "Prev"),
        ("right", "move(1)", "Next"),
        ("up", "move(-1)", ""),
        ("down", "move(1)", ""),
        ("tab", "move(1)", ""),
        ("shift+tab", "move(-1)", ""),
        ("enter", "activate", "Select"),
        ("y", "choose(True)", "Yes"),
        ("n", "choose(False)", "No"),
        ("escape", "choose(False)", "Cancel"),
    ]

    CSS = """
    /* Opaque backdrop: a translucent one lets the highlighted menu row behind
       bleed through as a stray colored band. */
    ConfirmModal { align: center middle; background: $background; }
    ConfirmModal #modal-box {
        width: 60; max-width: 90%; height: auto; padding: 1 2;
        border: round $panel; background: $surface;
    }
    ConfirmModal #modal-msg { padding: 0 0 1 0; }
    ConfirmModal #modal-buttons { height: auto; text-align: center; padding: 1 0 0 0; }
    """

    def __init__(self, message: str, *, yes_label: str = "yes", no_label: str = "no") -> None:
        super().__init__()
        self._message = message
        # index 0 = yes (True), index 1 = no (False); default to the safe choice.
        self._labels = [yes_label, no_label]
        self._index = 1

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Static(self._message, id="modal-msg")
            yield Static(self._buttons(), id="modal-buttons")

    def _buttons(self) -> Text:
        # Built as a Text (not markup) so the literal [ ] brackets aren't parsed
        # as markup tags.
        t = Text(justify="center")
        for i, label in enumerate(self._labels):
            if i:
                t.append("    ")
            if i == self._index:
                t.append(f"[ {label} ]", style=f"bold {ACCENT}")
            else:
                t.append(f"  {label}  ", style="dim")
        return t

    def _refresh(self) -> None:
        self.query_one("#modal-buttons", Static).update(self._buttons())

    def action_move(self, delta: int) -> None:
        self._index = (self._index + delta) % len(self._labels)
        self._refresh()

    def action_activate(self) -> None:
        self.dismiss(self._index == 0)

    def action_choose(self, value: bool) -> None:
        self.dismiss(value)
