"""ATS JSON blob adapter.

The ATS uses its OWN field names that do NOT match ours. The whole point of this adapter
is the explicit, visible mapping below — foreign key -> canonical path. Anything not in
the map is ignored (and logged); we never guess an unmapped field into a canonical one.
Provenance method is ``MAPPED`` so the remap is traceable.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Method
from .base import ExtractResult, SourceAdapter

# --- The visible contract: foreign ATS keys -> our canonical paths. ----------------- #
# Simple top-level fields (scalar or list-appended-to).
ATS_FIELD_MAP: dict[str, str] = {
    "candidateName": "full_name",
    "fullName": "full_name",
    "emailAddress": "emails",
    "email": "emails",
    "mobile": "phones",
    "phone": "phones",
    "headline": "headline",
    "summary": "headline",
    "yearsOfExperience": "years_experience",
    "locationCity": "location.city",
    "locationRegion": "location.region",
    "locationState": "location.region",
    "locationCountry": "location.country",
    "linkedinUrl": "links.linkedin",
    "githubUrl": "links.github",
    "portfolioUrl": "links.portfolio",
}

# Nested array fields get their own sub-maps (foreign item key -> canonical item key).
ATS_EDUCATION_MAP: dict[str, str] = {
    "school": "institution", "institution": "institution",
    "degree": "degree",
    "fieldOfStudy": "field", "major": "field",
    "gradYear": "end_year", "graduationYear": "end_year", "endYear": "end_year",
}
ATS_WORK_MAP: dict[str, str] = {
    "employer": "company", "company": "company",
    "role": "title", "title": "title",
    "startDate": "start", "endDate": "end",
    "description": "summary", "summary": "summary",
}
# Foreign keys for the array containers themselves.
_SKILLS_KEYS = ("skillSet", "skills", "skillTags")
_EDU_KEYS = ("education", "educationHistory", "schools")
_WORK_KEYS = ("workHistory", "experience", "employmentHistory")


class AtsJsonAdapter(SourceAdapter):
    source = "ats_json"

    def extract(self, path: Path) -> ExtractResult:
        result = ExtractResult()
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            result.warnings.append(f"{self.source}: empty file {path}")
            return result
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            result.warnings.append(f"{self.source}: invalid JSON in {path} ({exc})")
            return result
        if not isinstance(data, dict):
            result.warnings.append(f"{self.source}: top-level JSON is not an object in {path}")
            return result

        unmapped: list[str] = []
        for key, value in data.items():
            if key in ATS_FIELD_MAP:
                if value in (None, "", []):
                    continue
                result.claims.append(self._claim(ATS_FIELD_MAP[key], value, Method.MAPPED))
            elif key in _SKILLS_KEYS:
                self._emit_skills(value, result)
            elif key in _EDU_KEYS:
                self._emit_objects(value, ATS_EDUCATION_MAP, "education", result)
            elif key in _WORK_KEYS:
                self._emit_objects(value, ATS_WORK_MAP, "experience", result)
            else:
                unmapped.append(key)

        if unmapped:
            result.warnings.append(
                f"{self.source}: ignored unmapped fields {sorted(unmapped)} in {path}"
            )
        return result

    def _emit_skills(self, value: object, result: ExtractResult) -> None:
        if not isinstance(value, list):
            return
        for item in value:
            if isinstance(item, str) and item.strip():
                result.claims.append(self._claim("skills", item.strip(), Method.MAPPED))

    def _emit_objects(
        self, value: object, submap: dict[str, str], path: str, result: ExtractResult
    ) -> None:
        if not isinstance(value, list):
            return
        for item in value:
            if not isinstance(item, dict):
                continue
            mapped = {}
            for fk, fv in item.items():
                ck = submap.get(fk)
                if ck and fv not in (None, ""):
                    mapped[ck] = fv
            if mapped:
                result.claims.append(self._claim(path, mapped, Method.MAPPED))
