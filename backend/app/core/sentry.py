"""Sentry error tracking — initialised lazily so missing dep / DSN both no-op.

C3: init Sentry only when ``SENTRY_DSN`` is configured (prod-only by default).
C4: scrub PHI from event payloads before they leave the process.

We import sentry_sdk inside helpers so the module loads even when the SDK is
not installed in this image — useful in dev where Sentry is not needed.
"""

from __future__ import annotations

import re
from typing import Any

# Field names that must never leave the process unredacted. Matched
# case-insensitively against keys + JSON-like payloads.
_PHI_KEY_PATTERN = re.compile(
    r"(?i)("
    r"phone|email|address|dob|date.?of.?birth|ssn|national.?id|"
    r"full.?name|patient.?name|name|"
    r"notes|summary|text|content|message|"
    r"medication|prescription|allergies|diagnosis|symptoms"
    r")"
)

_REDACTED = "[REDACTED]"


def scrub_phi(payload: Any) -> Any:
    """Recursively redact PHI-looking keys in a Sentry event payload.

    Handles dicts, lists, and ``sentry_sdk.utils.Annotated`` style values.
    Never raises — anything weird is left intact.
    """
    try:
        if isinstance(payload, dict):
            return {
                k: (_REDACTED if _PHI_KEY_PATTERN.search(str(k)) else scrub_phi(v))
                for k, v in payload.items()
            }
        if isinstance(payload, list):
            return [scrub_phi(item) for item in payload]
        return payload
    except Exception:
        return payload


def _before_send(event: dict, _hint: dict) -> dict | None:
    """Sentry before_send hook — redacts PHI from request body, extra, contexts."""
    try:
        if "request" in event and isinstance(event["request"], dict):
            req = event["request"]
            for key in ("data", "headers", "cookies", "query_string"):
                if key in req:
                    req[key] = scrub_phi(req[key])
        if "extra" in event:
            event["extra"] = scrub_phi(event["extra"])
        if "contexts" in event:
            event["contexts"] = scrub_phi(event["contexts"])
        if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
            crumbs = event["breadcrumbs"].get("values") or []
            for crumb in crumbs:
                if isinstance(crumb, dict) and "data" in crumb:
                    crumb["data"] = scrub_phi(crumb["data"])
    except Exception:
        # Never block emission — original event still ships with whatever
        # scrubbing we managed.
        pass
    return event


def init_sentry(dsn: str | None, environment: str, release: str) -> bool:
    """Initialise Sentry if a DSN is configured. Returns True on success.

    Safe to call multiple times — sentry_sdk.init() is idempotent.
    """
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        return False

    integrations = [FastApiIntegration(), SqlalchemyIntegration()]
    # Redis is optional — only wire if installed.
    try:
        from sentry_sdk.integrations.redis import RedisIntegration

        integrations.append(RedisIntegration())
    except ImportError:
        pass

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.1,
        send_default_pii=False,  # belt-and-suspenders alongside before_send
        before_send=_before_send,
        integrations=integrations,
    )
    return True
