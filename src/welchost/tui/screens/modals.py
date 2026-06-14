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
        border: none; background: $surface;
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


class GhosttyRequiredModal(ModalScreen[None]):
    """A blocking gate shown when Ghostty isn't installed.

    Welchost configures a *Ghostty* banner, so without Ghostty there is nothing to
    do. This modal cannot be dismissed back to the menu — its single action is to
    quit: ``enter``, ``q``, and ``escape`` all exit the app.
    """

    BINDINGS = [
        ("enter", "quit", "Quit"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    CSS = """
    /* Opaque backdrop so the menu beneath is fully hidden — this is a dead end. */
    GhosttyRequiredModal { align: center middle; background: $background; }
    GhosttyRequiredModal #modal-box {
        width: 60; max-width: 90%; height: auto; padding: 1 2;
        border: none; background: $surface;
    }
    GhosttyRequiredModal #modal-msg { padding: 0 0 1 0; }
    GhosttyRequiredModal #modal-buttons { height: auto; text-align: center; padding: 1 0 0 0; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Static(self._message, id="modal-msg")
            yield Static(self._button(), id="modal-buttons")

    def _button(self) -> Text:
        # Text (not markup) so the literal [ ] brackets render verbatim.
        return Text("[ quit welchost ]", style=f"bold {ACCENT}", justify="center")

    def action_quit(self) -> None:
        self.app.exit()
