"""Phone normalization to E.164 (e.g. ``+14155552671``)."""

from __future__ import annotations

from typing import Optional

import phonenumbers

from . import DROP, NormResult


def normalize_phone(raw: object, region: Optional[str] = None) -> NormResult:
    """Parse ``raw`` to an E.164 string, or drop it.

    ``region`` is an ISO-3166 alpha-2 hint used only for numbers that carry no country
    code (e.g. a bare US number). It is derived from the candidate's own data, never
    guessed; if absent and the number has no country code, the value is dropped rather
    than assuming a country (honestly-empty beats wrong-but-confident).
    """
    if raw is None:
        return DROP
    text = str(raw).strip()
    if not text:
        return DROP
    try:
        parsed = phonenumbers.parse(text, region)
    except phonenumbers.NumberParseException:
        return DROP
    if not phonenumbers.is_valid_number(parsed):
        return DROP
    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return NormResult(formatted, False)
