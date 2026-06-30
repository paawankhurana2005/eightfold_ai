"""Email normalization: lowercase, trim, light RFC-ish validation."""

from __future__ import annotations

import re

from . import DROP, NormResult

# Deliberately conservative: good enough to reject obvious garbage without rejecting
# valid-but-unusual addresses. We are filtering noise, not enforcing the full RFC.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: object) -> NormResult:
    if raw is None:
        return DROP
    text = str(raw).strip().lower()
    if not text:
        return DROP
    # Strip a leading mailto: if present.
    if text.startswith("mailto:"):
        text = text[len("mailto:"):]
    if not _EMAIL_RE.match(text):
        return DROP
    return NormResult(text, False)
