"""Location normalization. Country -> ISO-3166 alpha-2; city/region trimmed pass-through."""

from __future__ import annotations

import pycountry

from . import DROP, NormResult

# Common informal spellings that ``pycountry`` does not match exactly.
_ALIASES = {
    "usa": "US", "u.s.": "US", "u.s.a.": "US", "united states of america": "US",
    "uk": "GB", "u.k.": "GB", "britain": "GB", "great britain": "GB", "england": "GB",
    "south korea": "KR", "korea": "KR", "north korea": "KP",
    "russia": "RU", "uae": "AE", "ksa": "SA", "ivory coast": "CI", "czech": "CZ",
}


def normalize_country(raw: object) -> NormResult:
    """Return an ISO-3166 alpha-2 code. Exact matches are non-fuzzy; ``search_fuzzy``
    hits are flagged fuzzy so the confidence model discounts them. Unknown -> dropped."""
    if raw is None:
        return DROP
    text = str(raw).strip()
    if not text:
        return DROP

    low = text.lower().rstrip(".")
    if low in _ALIASES:
        return NormResult(_ALIASES[low], False)

    # Already a 2-letter code?
    if len(text) == 2 and text.isalpha():
        rec = pycountry.countries.get(alpha_2=text.upper())
        if rec:
            return NormResult(rec.alpha_2, False)

    # 3-letter code?
    if len(text) == 3 and text.isalpha():
        rec = pycountry.countries.get(alpha_3=text.upper())
        if rec:
            return NormResult(rec.alpha_2, False)

    # Exact name lookups.
    for key in ("name", "official_name", "common_name"):
        try:
            rec = pycountry.countries.get(**{key: text})
        except Exception:
            rec = None
        if rec:
            return NormResult(rec.alpha_2, False)

    # Fuzzy fallback — flagged fuzzy.
    try:
        matches = pycountry.countries.search_fuzzy(text)
    except LookupError:
        matches = []
    if matches:
        return NormResult(matches[0].alpha_2, True)

    return DROP


def normalize_city(raw: object) -> NormResult:
    if raw is None:
        return DROP
    text = " ".join(str(raw).split()).strip()
    return NormResult(text, False) if text else DROP


def normalize_region(raw: object) -> NormResult:
    if raw is None:
        return DROP
    text = " ".join(str(raw).split()).strip()
    return NormResult(text, False) if text else DROP
