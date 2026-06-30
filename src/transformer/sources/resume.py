"""Resume adapter (PDF / DOCX / TXT prose) — the HIGHEST-risk source.

Scope is pinned by choice, not discovered later:
  * Reliable:    name, email, phone, skills (anchored patterns + a Skills section).
  * Best-effort: experience, education via deterministic regex / section heuristics,
                 emitted with the HEURISTIC method so the confidence model discounts
                 them (x0.9) and a structured source always outranks them.
No ML / NLP — determinism and explainability over recall.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Method
from .base import ExtractResult, SourceAdapter

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().\-]{7,}\d)")
_YEAR = r"(?:[A-Za-z]{3,9}\.?\s+)?\d{4}|\d{1,2}[/-]\d{4}"
_DATE_RANGE = re.compile(
    rf"({_YEAR})\s*(?:-|–|—|to)\s*({_YEAR}|present|current)", re.IGNORECASE
)
_DEGREE_RE = re.compile(
    r"\b(b\.?s\.?|b\.?a\.?|bachelor|m\.?s\.?|m\.?a\.?|master|mba|ph\.?d\.?|doctorate)\b",
    re.IGNORECASE,
)

_HEADERS = {
    "skills": "skills", "technical skills": "skills", "core skills": "skills",
    "technologies": "skills", "tech stack": "skills",
    "experience": "experience", "work experience": "experience",
    "professional experience": "experience", "employment": "experience",
    "employment history": "experience",
    "education": "education", "academic background": "education",
    "summary": "summary", "profile": "summary", "objective": "summary",
    # Recognized so they (a) terminate the experience/education sections instead of
    # bleeding into them, and (b) get excluded from candidate-contact scanning. We do
    # not extract anything from their bodies.
    "projects": "projects", "personal projects": "projects",
    "selected projects": "projects", "side projects": "projects",
    "references": "references",
}

# Sections that list OTHER people's contacts (references) or third-party project info.
# Their lines are excluded from the candidate's OWN email/phone scan so a References
# block can't silently contaminate the candidate's contact claims.
_NON_CANDIDATE_SECTIONS = {"references", "projects"}

# Skill-tier sub-labels ("Proficient: ...", "Familiar: ...") and column headers. These
# are list labels, not skills, so they're dropped while the skills under them are kept.
_TIER_LABELS = frozenset({
    "proficient", "experienced", "familiar", "expert", "advanced", "intermediate",
    "beginner", "skilled", "languages", "frameworks", "tools", "databases",
    "technologies", "libraries",
})


class ResumeAdapter(SourceAdapter):
    source = "resume"

    def extract(self, path: Path) -> ExtractResult:
        result = ExtractResult()
        text = self._read_text(Path(path), result)
        if not text or not text.strip():
            if not result.warnings:
                result.warnings.append(f"{self.source}: no extractable text in {path}")
            return result

        lines = [ln.rstrip() for ln in text.splitlines()]
        # Scan for the candidate's own email/phone over everything EXCEPT reference /
        # project sections (which carry third-party contacts). Name still uses the top.
        reliable_text = "\n".join(self._candidate_lines(lines))
        self._extract_reliable(reliable_text, lines, result)
        sections = self._sections(lines)
        self._extract_skills(sections.get("skills", ""), result)
        self._extract_experience(sections.get("experience", ""), result)
        self._extract_education(sections.get("education", ""), result)
        if "summary" in sections and sections["summary"].strip():
            headline = " ".join(sections["summary"].split())[:200]
            result.claims.append(self._claim("headline", headline, Method.HEURISTIC))
        return result

    # --- text extraction ------------------------------------------------------------- #
    def _read_text(self, path: Path, result: ExtractResult) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            import pdfplumber

            chunks = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    chunks.append(page.extract_text() or "")
            return "\n".join(chunks)
        if suffix == ".docx":
            import docx

            document = docx.Document(str(path))
            return "\n".join(p.text for p in document.paragraphs)
        if suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="replace")
        result.warnings.append(f"{self.source}: unsupported resume type {suffix} for {path}")
        return ""

    # --- reliable fields ------------------------------------------------------------- #
    def _extract_reliable(self, text: str, lines: list[str], result: ExtractResult) -> None:
        for email in dict.fromkeys(_EMAIL_RE.findall(text)):
            result.claims.append(self._claim("emails", email, Method.REGEX))
        for phone in dict.fromkeys(_PHONE_RE.findall(text)):
            result.claims.append(self._claim("phones", phone.strip(), Method.REGEX))
        name = self._guess_name(lines)
        if name:
            result.claims.append(self._claim("full_name", name, Method.HEURISTIC))

    def _guess_name(self, lines: list[str]) -> str | None:
        for raw in lines[:6]:
            line = raw.strip()
            if not line or "@" in line or any(c.isdigit() for c in line):
                continue
            if line.lower().rstrip(":") in _HEADERS:
                continue
            tokens = line.split()
            if 2 <= len(tokens) <= 4 and all(t[0].isupper() for t in tokens if t and t[0].isalpha()):
                if all(re.fullmatch(r"[A-Za-z.\-']+", t) for t in tokens):
                    return line
        return None

    def _candidate_lines(self, lines: list[str]) -> list[str]:
        """Lines eligible to hold the candidate's own contact info: the preamble plus
        every section other than references/projects. Excluding those sections is what
        stops a References block's emails/phones from being claimed as the candidate's.
        """
        out: list[str] = []
        current: str | None = None
        for raw in lines:
            key = self._header_key(raw)
            if key is not None:
                current = key
                continue  # drop the header line itself
            if current in _NON_CANDIDATE_SECTIONS:
                continue
            out.append(raw)
        return out

    # --- section splitting ----------------------------------------------------------- #
    def _sections(self, lines: list[str]) -> dict[str, str]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for raw in lines:
            key = self._header_key(raw)
            if key:
                current = key
                sections.setdefault(current, [])
                continue
            if current:
                sections[current].append(raw)
        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def _header_key(self, line: str) -> str | None:
        stripped = line.strip().rstrip(":").lower()
        if stripped in _HEADERS and len(line.strip()) <= 40:
            return _HEADERS[stripped]
        return None

    # --- best-effort sections -------------------------------------------------------- #
    def _extract_skills(self, body: str, result: ExtractResult) -> None:
        if not body:
            return
        # Split on ":" too so tier sub-labels detach from the first skill on their line
        # ("Proficient: Python" -> "Proficient", "Python"); the label is then dropped.
        tokens = re.split(r"[,\n;:•|/]+", body)
        for tok in tokens:
            skill = tok.strip(" \t-•")
            if skill and len(skill) <= 40 and skill.lower() not in _TIER_LABELS:
                result.claims.append(self._claim("skills", skill, Method.REGEX))

    def _extract_experience(self, body: str, result: ExtractResult) -> None:
        if not body:
            return
        for line in body.splitlines():
            line = line.strip(" \t-•")
            if not line:
                continue
            m = _DATE_RANGE.search(line)
            if not m:
                continue
            start_raw, end_raw = m.group(1), m.group(2)
            head = line[: m.start()].strip(" \t-–—,")
            company, title = self._split_company_title(head)
            entry = {
                "company": company, "title": title,
                "start": start_raw,
                "end": None if end_raw.lower() in ("present", "current") else end_raw,
                "summary": line,
            }
            result.claims.append(self._claim("experience", entry, Method.HEURISTIC))

    def _split_company_title(self, head: str) -> tuple[str | None, str | None]:
        for sep in (" — ", " – ", " - ", " at ", ", ", " @ "):
            if sep in head:
                left, right = head.split(sep, 1)
                # Convention in our samples: "Title at Company" or "Company - Title".
                if sep == " at ":
                    return right.strip() or None, left.strip() or None
                return left.strip() or None, right.strip() or None
        return (head or None), None

    def _extract_education(self, body: str, result: ExtractResult) -> None:
        if not body:
            return
        for line in body.splitlines():
            line = line.strip(" \t-•")
            if not line:
                continue
            year_m = re.search(r"\b(19|20)\d{2}\b", line)
            degree_m = _DEGREE_RE.search(line)
            if not (year_m or degree_m):
                continue
            entry: dict = {"summary": line}
            if year_m:
                entry["end_year"] = year_m.group(0)
            if degree_m:
                entry["degree"] = degree_m.group(0)
            # Institution heuristic: a clause mentioning University/College/Institute.
            inst_m = re.search(r"[A-Z][\w.&'\- ]*(University|College|Institute|School)", line)
            if inst_m:
                entry["institution"] = inst_m.group(0).strip()
            entry.pop("summary", None)
            if entry:
                result.claims.append(self._claim("education", entry, Method.HEURISTIC))
