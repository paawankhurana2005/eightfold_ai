"""Confidence model — concrete, deterministic math.

per_field = base_trust(winning_source)
          + 0.05 * min(independent_corroborations, 3)   # +0.05 each, capped at +0.15
per_field = per_field * 0.9   if the winning value came from a fuzzy/regex method
per_field = clamp(per_field, FLOOR, 0.99)               # never 1.0 — nothing is certain

overall_confidence = mean of per-field confidences weighted by field importance
(identity fields weighted higher than headline/skills).
"""

from __future__ import annotations

# Base trust per source.
TRUST: dict[str, float] = {
    "ats_json": 0.90,
    "recruiter_csv": 0.85,
    "resume": 0.60,
    "github": 0.50,
    "recruiter_notes": 0.35,
}
DEFAULT_TRUST = 0.30
FLOOR = 0.05
CEIL = 0.99
CORROBORATION_STEP = 0.05
CORROBORATION_CAP = 3  # so the agreement bonus tops out at +0.15
FUZZY_FACTOR = 0.9

# Field importance for the overall weighted mean. Identity fields dominate.
IMPORTANCE: dict[str, float] = {
    "full_name": 3.0,
    "emails": 3.0,
    "phones": 3.0,
    "years_experience": 1.5,
    "location": 1.5,
    "experience": 1.5,
    "skills": 1.0,
    "education": 1.0,
    "headline": 1.0,
    "links": 0.5,
}
DEFAULT_IMPORTANCE = 1.0


def base_trust(source: str) -> float:
    return TRUST.get(source, DEFAULT_TRUST)


def clamp(value: float) -> float:
    return max(FLOOR, min(CEIL, value))


def rank(source: str) -> float:
    """Higher = more trusted. Used to pick scalar winners."""
    return base_trust(source)


def field_confidence(winning_source: str, corroborations: int, fuzzy: bool) -> float:
    """Confidence for one field given its winning source, how many *other* independent
    sources agreed on the normalized value, and whether the value was fuzzy/regex-derived.
    """
    score = base_trust(winning_source)
    score += CORROBORATION_STEP * min(max(corroborations, 0), CORROBORATION_CAP)
    if fuzzy:
        score *= FUZZY_FACTOR
    return round(clamp(score), 4)


def overall_confidence(field_conf: dict[str, float]) -> float:
    """Importance-weighted mean over populated fields. Empty -> 0.0."""
    num = 0.0
    den = 0.0
    for field, conf in field_conf.items():
        weight = IMPORTANCE.get(field, DEFAULT_IMPORTANCE)
        num += weight * conf
        den += weight
    return round(num / den, 4) if den else 0.0
