"""Skill canonicalization via the alias dictionary."""

from __future__ import annotations

from . import DROP, NormResult
from ..skills_dictionary import ALIAS_INDEX


def canonicalize_skill(raw: object) -> NormResult:
    """Map a raw skill string to its canonical name.

    Known aliases resolve to the canonical taxonomy name. Unknown skills are kept (not
    dropped) but title-cased, so we never lose a real skill — we just can't promise it
    matches the taxonomy.
    """
    if raw is None:
        return DROP
    text = " ".join(str(raw).split()).strip()
    if not text:
        return DROP
    canonical = ALIAS_INDEX.get(text.lower())
    if canonical:
        return NormResult(canonical, False)
    # Unknown skill: keep it (never drop a real skill), but only re-case all-lowercase
    # input. All-caps is left alone so acronyms like "CSS"/"HTML" aren't mangled.
    return NormResult(text.title() if text.islower() else text, False)
