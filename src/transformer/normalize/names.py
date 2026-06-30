"""Name normalization: collapse whitespace; fix obviously broken casing only."""

from __future__ import annotations

from . import DROP, NormResult


def normalize_name(raw: object) -> NormResult:
    if raw is None:
        return DROP
    text = " ".join(str(raw).split()).strip()
    if not text:
        return DROP
    # Only re-case when the input is uniformly upper or lower; otherwise preserve the
    # original casing so we don't mangle names like "McDonald" or "van der Berg".
    if text.isupper() or text.islower():
        text = text.title()
    return NormResult(text, False)
