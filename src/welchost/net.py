"""Shared TLS context for the core's outbound HTTPS calls.

macOS Python builds from python.org frequently ship without a usable CA bundle,
so a plain ``urllib`` HTTPS request raises ``CERTIFICATE_VERIFY_FAILED`` even
though the network is fine. We prefer :mod:`certifi`'s bundle when importable and
fall back to the system default context otherwise, so both the PyPI update check
(:mod:`welchost.update`) and the telemetry ping (:mod:`welchost.telemetry`) work
regardless of how the user's Python was installed.
"""

from __future__ import annotations

import ssl

_CTX: ssl.SSLContext | None = None


def ssl_context() -> ssl.SSLContext:
    """A verifying TLS context, backed by certifi's CA bundle when available.

    Built once and cached. Falls back to the stdlib default context if certifi
    is somehow absent, so this never raises on import or first use.
    """
    global _CTX
    if _CTX is None:
        try:
            import certifi

            _CTX = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _CTX = ssl.create_default_context()
    return _CTX
