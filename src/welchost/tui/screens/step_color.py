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
        apply_visibility(self, {f"solid-box-{idx}": not is_grad, f"grad-box-{idx}": is_grad})

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
