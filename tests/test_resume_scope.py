"""Tests pinning the resume adapter's scope: reliable identity/skills, best-effort the rest."""

from __future__ import annotations

from transformer.models import is_fuzzy_method
from transformer.sources import ResumeAdapter

RESUME = """Dana Lopez
dana.lopez@example.com | +1 (212) 555-0143

Skills
Python, Go, Kubernetes

Experience
Senior Engineer at Globex   Jun 2017 - Feb 2021

Education
State University, BS Computer Science, 2014
"""


def _by_path(claims):
    out = {}
    for c in claims:
        out.setdefault(c.path, []).append(c)
    return out


def test_reliable_fields_extracted(tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text(RESUME)
    by_path = _by_path(ResumeAdapter().extract(f).claims)
    assert by_path["emails"][0].value == "dana.lopez@example.com"
    assert "+1" in by_path["phones"][0].value
    assert by_path["full_name"][0].value == "Dana Lopez"
    skills = {c.value for c in by_path["skills"]}
    assert {"Python", "Go", "Kubernetes"} <= skills


def test_experience_and_education_are_heuristic_low_confidence(tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text(RESUME)
    by_path = _by_path(ResumeAdapter().extract(f).claims)
    # Experience/education come out via fuzzy heuristics by design.
    assert all(is_fuzzy_method(c.method) for c in by_path.get("experience", []))
    assert all(is_fuzzy_method(c.method) for c in by_path.get("education", []))
    exp = by_path["experience"][0].value
    assert exp["company"] == "Globex" and exp["title"] == "Senior Engineer"


def test_missing_text_does_not_crash(tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text("")
    res = ResumeAdapter().safe_extract(f)
    assert res.claims == [] and res.warnings
