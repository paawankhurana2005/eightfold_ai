"""Recruiter notes (.txt) — free text, the lowest-trust source.

We extract only what we can anchor confidently: emails, phones, an explicit years-of-
experience mention, and skills that appear after a skill-context phrase ("proficient in
…"). We deliberately do NOT guess a name or scan loose words for skills — notes are
lowest-trust and inventing here would be exactly the "wrong-but-confident" failure.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Method
from .base import ExtractResult, SourceAdapter

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().\-]{7,}\d)")
_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:years|yrs)\b", re.IGNORECASE)
_SKILL_CONTEXT_RE = re.compile(
    r"(?:proficient in|skilled in|experience with|expertise in|strong in|knows|good at)\s+"
    r"([^.\n;]+)",
    re.IGNORECASE,
)


class RecruiterNotesAdapter(SourceAdapter):
    source = "recruiter_notes"

    def extract(self, path: Path) -> ExtractResult:
        result = ExtractResult()
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            result.warnings.append(f"{self.source}: empty file {path}")
            return result

        for email in dict.fromkeys(_EMAIL_RE.findall(text)):
            result.claims.append(self._claim("emails", email, Method.REGEX))
        for phone in dict.fromkeys(_PHONE_RE.findall(text)):
            result.claims.append(self._claim("phones", phone.strip(), Method.REGEX))

        ym = _YEARS_RE.search(text)
        if ym:
            result.claims.append(self._claim("years_experience", int(ym.group(1)), Method.REGEX))

        for match in _SKILL_CONTEXT_RE.findall(text):
            for token in re.split(r"[,/]| and ", match):
                skill = token.strip(" \t.")
                if skill and len(skill) <= 40:
                    result.claims.append(self._claim("skills", skill, Method.REGEX))
        return result
