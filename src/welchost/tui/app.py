"""Textual application entry point for welchost."""

from __future__ import annotations

from textual import work
from textual.app import App

from .. import detect
from ..config import WelchostConfig, load_config
from .widgets import BannerPreview


class WelchostApp(App):
    """The welchost TUI.

    Holds a single working :class:`WelchostConfig` (``self.model``) that every
    screen mutates and previews live.
    """

    TITLE = "welchost"
    SUB_TITLE = "a welcome screen for Ghostty"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    CSS = """
    Screen { align: center top; }
    #menu-box, #wizard-body { width: 72; max-width: 100%; padding: 1 2; }
    .panel-title { text-style: bold; padding: 1 0 0 1; color: $text-muted; }
    .hint { color: $text-muted; padding: 1 2; }
    .section-label { text-style: bold; padding: 1 0 0 0; }
    ListView { padding: 0; margin: 1 0; }
    ListItem { padding: 0 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        loaded = load_config()
        self.had_config: bool = loaded is not None
        self.model: WelchostConfig = loaded or WelchostConfig.default()

    def on_mount(self) -> None:
        from .screens.main_menu import MainMenu

        if self.had_config:
            from .screens.main_menu import EditMenu

            self.push_screen(EditMenu())
        else:
            self.push_screen(MainMenu())

        # Ghostty is required for the banner to ever render, so if it's missing we
        # block the UI behind a quit-only modal rather than let the user configure
        # something that can't display. Skip the update/telemetry pings — the only
        # path forward is to quit. (No-op in dev; see detect.)
        if detect.should_warn_no_ghostty():
            from .screens.modals import GhosttyRequiredModal

            self.push_screen(GhosttyRequiredModal(detect.GHOSTTY_REQUIRED_MESSAGE))
            return

        # Check PyPI for a newer release and offer to update (skipped in dev — no
        # nagging while hacking). Telemetry does its own gating (dev/key/consent),
        # so call it unconditionally; it no-ops in dev unless WELCHOST_TELEMETRY_FORCE
        # is set, the hatch that lets the opt-in prompt be exercised in dev.
        if not detect.is_dev():
            self._check_for_update()
        self._send_telemetry()

    # --- self-update -----------------------------------------------------------
    # On launch, check PyPI in a background thread (so the network call never
    # blocks or delays the UI) and, if a newer version exists, prompt the user.
    # Failures (offline, timeout) are silent — the worker just finds nothing.

    @work(thread=True, exclusive=True, group="update-check")
    def _check_for_update(self) -> None:
        from ..update import current_version, is_newer, latest_version

        latest = latest_version()
        if latest and is_newer(latest, current_version()):
            self.call_from_thread(self._prompt_update, latest)

    def _prompt_update(self, latest: str) -> None:
        from ..update import current_version
        from .screens.modals import ConfirmModal

        message = (
            f"welchost [b]v{latest}[/b] is available (you have v{current_version()}).\nUpdate now?"
        )

        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                self._run_update()

        self.push_screen(ConfirmModal(message, yes_label="update", no_label="later"), on_result)

    @work(thread=True, exclusive=True, group="update-run")
    def _run_update(self) -> None:
        from ..update import detect_install_method, run_upgrade

        method = detect_install_method()
        self.call_from_thread(self.notify, f"Updating welchost via {method}…", timeout=4)
        ok, output = run_upgrade(method)
        if ok:
            self.call_from_thread(
                self.notify,
                "Updated. Restart welchost to use the new version.",
                timeout=8,
            )
        else:
            self.call_from_thread(
                self.notify,
                f"Update failed: {output[-180:] or 'unknown error'}",
                severity="error",
                timeout=10,
            )

    # --- telemetry -----------------------------------------------------------
    # Opt-in usage analytics (no PII). On first run we prompt for consent in a
    # modal; nothing is sent until the user agrees. After that, each launch sends
    # one anonymous ping from a background thread so it never blocks the UI.
    # Disabled without a key, in dev mode, or via WELCHOST_NO_TELEMETRY / DO_NOT_TRACK.

    @work(thread=True, exclusive=True, group="telemetry")
    def _send_telemetry(self) -> None:
        from ..telemetry import needs_consent_prompt, track_launch

        if needs_consent_prompt():
            self.call_from_thread(self._prompt_consent)
        else:
            track_launch()

    def _prompt_consent(self) -> None:
        from .screens.modals import ConfirmModal

        message = (
            "Share anonymous usage stats? No personal data — just OS, welchost "
            "version, and launch counts, so we can see how many people use it."
        )

        def on_result(confirmed: bool | None) -> None:
            self._record_consent(bool(confirmed))

        self.push_screen(ConfirmModal(message, yes_label="share", no_label="no thanks"), on_result)

    @work(thread=True, exclusive=True, group="telemetry-consent")
    def _record_consent(self, granted: bool) -> None:
        from ..telemetry import record_consent

        record_consent(granted)

    # --- config lifecycle ----------------------------------------------------
    # `model` is the working config; `had_config` tracks whether a config exists
    # on disk. These three helpers are the only places that mutate that pair, so
    # the state stays consistent across save / delete / new-build flows.

    def adopt_config(self, model: WelchostConfig) -> None:
        """Record `model` as the now-installed config (call after a save)."""
        self.model = model
        self.had_config = True

    def clear_config(self) -> None:
        """Reset to defaults with nothing installed (call after delete/reset)."""
        self.model = WelchostConfig.default()
        self.had_config = False

    def new_draft(self) -> None:
        """Start a fresh in-memory config for a new build. The on-disk files are
        untouched until the user saves, so `had_config` is intentionally left as
        is rather than flipped — it reflects disk, not the editor."""
        self.model = WelchostConfig.default()

    def refresh_preview(self) -> None:
        """Re-render every mounted BannerPreview from the current model.

        Queries the active screen, not the app: in Textual 8.x ``App.query``
        does not descend into the current screen's tree, so ``self.query`` here
        would match nothing and the preview would never render.
        """
        for preview in self.screen.query(BannerPreview):
            preview.show(self.model)


def run() -> None:
    """Launch the app (starts the dev hot-reload watcher in DEV mode)."""
    if detect.is_dev():
        try:
            from .dev_watcher import start_watcher

            start_watcher()
        except Exception:
            pass
    WelchostApp().run()
