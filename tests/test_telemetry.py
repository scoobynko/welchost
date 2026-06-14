"""Telemetry: opt-in consent gates, anonymous-id persistence, payload shape.

No test ever touches the network — `urlopen` is monkeypatched to a recorder (or
to raise, to prove disabled paths send nothing). `fake_home` keeps the sidecar
file under a throwaway dir.
"""

from __future__ import annotations

import json

import pytest

from welchost import telemetry


class _FakeResp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def captured(monkeypatch):
    """Record every POST instead of sending it. Returns the list of requests."""
    calls = []

    def fake_urlopen(req, timeout=None, **kwargs):
        calls.append(req)
        return _FakeResp()

    monkeypatch.setattr(telemetry.urllib.request, "urlopen", fake_urlopen)
    return calls


@pytest.fixture
def configured(monkeypatch):
    """Embed a fake key and clear opt-out vars so telemetry is *configured*
    (permitted to run) — but still gated on consent until granted."""
    monkeypatch.setattr(telemetry, "POSTHOG_API_KEY", "phc_test")
    monkeypatch.delenv("WELCHOST_NO_TELEMETRY", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("WELCHOST_TELEMETRY_FORCE", raising=False)


def _events(captured):
    return [json.loads(r.data)["event"] for r in captured]


def _no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("telemetry must not hit the network when disabled")

    monkeypatch.setattr(telemetry.urllib.request, "urlopen", boom)


# --- configuration gates (independent of consent) -------------------------


def test_disabled_without_key(fake_home, monkeypatch):
    """The shipped default (empty key) is a hard no-op — no prompt, no network."""
    monkeypatch.setattr(telemetry, "POSTHOG_API_KEY", "")
    _no_network(monkeypatch)
    assert telemetry.is_configured() is False
    assert telemetry.needs_consent_prompt() is False
    telemetry.track_launch()  # no-op, must not raise/send
    assert not telemetry._state_path().exists()


def test_opt_out_env_blocks_configuration(fake_home, configured, monkeypatch):
    monkeypatch.setenv("WELCHOST_NO_TELEMETRY", "1")
    _no_network(monkeypatch)
    assert telemetry.is_configured() is False
    assert telemetry.needs_consent_prompt() is False


def test_do_not_track_env_blocks_configuration(fake_home, configured, monkeypatch):
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    _no_network(monkeypatch)
    assert telemetry.is_configured() is False


def test_dev_mode_blocks_unless_forced(fake_home, configured, monkeypatch):
    from welchost import detect

    detect.DEV_MODE = True
    _no_network(monkeypatch)
    assert telemetry.is_configured() is False

    # The force hatch re-enables configuration in dev so the prompt is testable.
    monkeypatch.setenv("WELCHOST_TELEMETRY_FORCE", "1")
    assert telemetry.is_configured() is True
    assert telemetry.needs_consent_prompt() is True


# --- consent gating -------------------------------------------------------


def test_nothing_sent_before_consent(fake_home, configured, monkeypatch):
    """Configured but undecided: prompt is needed, and a stray track_launch sends
    nothing (opt-in means silence until the user agrees)."""
    _no_network(monkeypatch)
    assert telemetry.consent_state() == "unset"
    assert telemetry.needs_consent_prompt() is True
    assert telemetry.is_enabled() is False
    telemetry.track_launch()  # must not send
    assert not telemetry._state_path().exists()


def test_grant_sends_install_and_launch(fake_home, configured, captured):
    telemetry.record_consent(True)
    assert _events(captured) == ["install", "launch"]
    assert telemetry.consent_state() == "granted"
    assert telemetry.needs_consent_prompt() is False
    assert telemetry.is_enabled() is True

    distinct_id = json.loads(telemetry._state_path().read_text())["distinct_id"]
    captured.clear()

    # A subsequent normal launch sends only "launch", same identity.
    telemetry.track_launch()
    assert _events(captured) == ["launch"]
    assert json.loads(captured[0].data)["distinct_id"] == distinct_id


def test_decline_sends_nothing_and_is_remembered(fake_home, configured, captured):
    telemetry.record_consent(False)
    assert _events(captured) == []  # no events on decline
    assert telemetry.consent_state() == "declined"
    assert telemetry.needs_consent_prompt() is False  # never ask again

    telemetry.track_launch()
    assert _events(captured) == []  # still silent


def test_payload_shape(fake_home, configured, captured):
    telemetry.record_consent(True)
    body = json.loads(captured[-1].data)
    assert body["api_key"] == "phc_test"
    assert body["distinct_id"]
    props = body["properties"]
    # Coarse, non-identifying facts only — and person profiles disabled.
    assert props["$process_person_profile"] is False
    assert props["welchost_version"]
    assert "os" in props and "arch" in props and "python" in props
    # Nothing that could identify a user.
    assert not any(k in props for k in ("user", "username", "ip", "hostname", "path"))


def test_record_consent_is_soft_on_network_error(fake_home, configured, monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(telemetry.urllib.request, "urlopen", boom)
    # Must not raise; the decision still persists even though the POST failed.
    telemetry.record_consent(True)
    assert telemetry.consent_state() == "granted"


def test_unpersisted_consent_reprompts(fake_home, configured, captured, monkeypatch):
    """If the decision can't be persisted (read-only dir), this session still
    honors a grant (sends), but consent reads back as unset so we re-prompt next
    launch rather than silently dropping telemetry."""

    def cant_write(*a, **k):
        raise OSError("read-only config dir")

    monkeypatch.setattr(telemetry.detect, "ensure_config_dir", cant_write)

    telemetry.record_consent(True)
    assert _events(captured) == ["install", "launch"]  # this session still sent
    assert not telemetry._state_path().exists()
    assert telemetry.consent_state() == "unset"
    assert telemetry.needs_consent_prompt() is True


def test_reset_removes_analytics_json(fake_home, configured, captured):
    """generator.reset() must clean up the telemetry sidecar it owns."""
    from welchost import generator

    telemetry.record_consent(True)
    assert telemetry._state_path().exists()

    generator.reset()
    assert not telemetry._state_path().exists()
