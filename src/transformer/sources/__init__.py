"""Source adapters and the filename-based detection used by ingest."""

from __future__ import annotations

from .ats_json import AtsJsonAdapter
from .base import ExtractResult, SourceAdapter
from .github import GithubAdapter
from .recruiter_csv import RecruiterCsvAdapter
from .recruiter_notes import RecruiterNotesAdapter
from .resume import ResumeAdapter

__all__ = [
    "ExtractResult",
    "SourceAdapter",
    "AtsJsonAdapter",
    "GithubAdapter",
    "RecruiterCsvAdapter",
    "RecruiterNotesAdapter",
    "ResumeAdapter",
    "detect_source",
]


def detect_source(filename: str) -> str | None:
    """Map a filename to a source id using deterministic conventions.

    Conventions (case-insensitive):
        *.csv                      -> recruiter_csv
        ats*.json / *.ats.json     -> ats_json
        github*.json / github.url  -> github
        *.pdf / *.docx / resume.*  -> resume
        notes*.txt / *.notes.txt   -> recruiter_notes
    """
    name = filename.lower()
    if name.endswith(".csv"):
        return "recruiter_csv"
    if name.startswith("github") or name.startswith("gh."):
        if name.endswith((".json", ".url", ".txt")):
            return "github"
    if name.endswith(".json"):  # remaining json -> ats (after github handled above)
        return "ats_json"
    if name.endswith((".pdf", ".docx")):
        return "resume"
    if name.startswith("resume."):
        return "resume"
    if "notes" in name and name.endswith(".txt"):
        return "recruiter_notes"
    if name.endswith(".txt"):
        return "recruiter_notes"
    return None
