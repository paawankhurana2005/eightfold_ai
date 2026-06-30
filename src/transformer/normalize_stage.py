"""Normalize stage: raw claims -> normalized claims.

Dispatches each claim to the right pure normalizer based on its canonical path. A claim
whose value fails to normalize is dropped (the field stays empty) — never invented. Fuzzy
normalization (e.g. fuzzy country match) OR-s its flag onto the claim so the confidence
model can discount it.
"""

from __future__ import annotations

from .models import FieldClaim
from .normalize import (
    canonicalize_skill,
    normalize_city,
    normalize_country,
    normalize_email,
    normalize_month,
    normalize_name,
    normalize_phone,
    normalize_region,
)


def _phone_region_hint(claims: list[FieldClaim]) -> str | None:
    """Derive an ISO-3166 region from the candidate's own country claims (not a guess).

    Used only to parse phone numbers that carry no country code.
    """
    for claim in claims:
        if claim.path == "location.country":
            res = normalize_country(claim.value)
            if res.value:
                return res.value
    return None


def _passthrough(value: object) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None


def _number(value: object) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num


def _normalize_experience(value: dict) -> dict | None:
    out: dict = {}
    for key in ("company", "title", "summary"):
        text = _passthrough(value.get(key))
        if text:
            out[key] = text
    for key in ("start", "end"):
        raw = value.get(key)
        if raw:
            res = normalize_month(raw)
            if res.value:
                out[key] = res.value
    return out or None


def _normalize_education(value: dict) -> dict | None:
    out: dict = {}
    for key in ("institution", "degree", "field"):
        text = _passthrough(value.get(key))
        if text:
            out[key] = text
    raw_year = value.get("end_year")
    if raw_year is not None:
        try:
            year = int(str(raw_year)[:4])
            if 1900 <= year <= 2100:
                out["end_year"] = year
        except (TypeError, ValueError):
            pass
    return out or None


def normalize_claims(claims: list[FieldClaim]) -> list[FieldClaim]:
    region = _phone_region_hint(claims)
    out: list[FieldClaim] = []

    for claim in claims:
        path = claim.path
        value = claim.value
        fuzzy = claim.fuzzy
        new_value: object = None

        if path == "full_name":
            new_value, fz = normalize_name(value)
            fuzzy = fuzzy or fz
        elif path == "emails":
            new_value, fz = normalize_email(value)
            fuzzy = fuzzy or fz
        elif path == "phones":
            new_value, fz = normalize_phone(value, region)
            fuzzy = fuzzy or fz
        elif path == "location.city":
            new_value, fz = normalize_city(value)
            fuzzy = fuzzy or fz
        elif path == "location.region":
            new_value, fz = normalize_region(value)
            fuzzy = fuzzy or fz
        elif path == "location.country":
            new_value, fz = normalize_country(value)
            fuzzy = fuzzy or fz
        elif path == "skills":
            new_value, fz = canonicalize_skill(value)
            fuzzy = fuzzy or fz
        elif path == "years_experience":
            new_value = _number(value)
        elif path == "headline" or path.startswith("links."):
            new_value = _passthrough(value)
        elif path == "experience":
            new_value = _normalize_experience(value) if isinstance(value, dict) else None
        elif path == "education":
            new_value = _normalize_education(value) if isinstance(value, dict) else None
        else:
            new_value = _passthrough(value)

        if new_value is None or new_value == "":
            continue
        out.append(
            FieldClaim(path=path, value=new_value, source=claim.source,
                       method=claim.method, fuzzy=fuzzy)
        )
    return out
