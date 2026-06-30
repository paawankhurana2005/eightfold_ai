"""Adversarial resume parsing — the alex-rivera sample exists to stress exactly these.

Each test pins one parsing risk the resume adapter has to survive. We run the REAL committed ``samples/inputs/alex-rivera/resume.pdf`` (the lossy binary
format — this also proves the adapter is format-robust, not just docx-robust).
"""

from __future__ import annotations

import pytest

from transformer.sources import ResumeAdapter

# The two reference contacts in the resume. The candidate's OWN contacts must never
# include these — that's the headline adversarial case.
REF_EMAILS = {"john.doe@email.com", "maria.chen@email.com"}
REF_PHONE_DIGITS = {"2065550144", "2065550177"}


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


@pytest.fixture
def claims(samples_dir):
    resume = samples_dir / "inputs" / "alex-rivera" / "resume.pdf"
    by_path: dict[str, list] = {}
    for c in ResumeAdapter().extract(resume).claims:
        by_path.setdefault(c.path, []).append(c)
    return by_path


def test_ongoing_role_has_null_end_date(claims):
    """'May 2021 - Current' must resolve to start=2021-05, end=None — never an invented end."""
    exp = [c.value for c in claims["experience"]]
    ongoing = [e for e in exp if e["company"] == "Cloudscale Systems"]
    assert len(ongoing) == 1
    entry = ongoing[0]
    assert entry["start"] == "May 2021"          # raw; normalized to 2021-05 downstream
    assert entry["end"] is None                  # ongoing -> honestly empty, not faked


def test_three_jobs_extracted_with_distinct_date_formats(claims):
    companies = {c.value["company"] for c in claims["experience"]}
    assert companies == {"Cloudscale Systems", "Brightline Analytics", "Harbor Logistics"}
    assert len(claims["experience"]) == 3


def test_projects_not_misparsed_as_experience(claims):
    """The Projects section (Chess Engine in C++, chatbot in C#) must not become jobs."""
    blob = " ".join(str(c.value) for c in claims["experience"]).lower()
    assert "chess" not in blob
    assert "chatbot" not in blob
    assert "c++" not in blob and "c#" not in blob


def test_all_three_skill_tiers_extracted(claims):
    """Every skill across Proficient / Experienced / Familiar — not just the first tier."""
    skills = {c.value.lower() for c in claims["skills"]}
    expected = {
        # Proficient
        "python", "javascript", "typescript", "sql",
        # Experienced
        "react", "django", "node.js", "docker", "postgresql",
        # Familiar
        "rust", "go", "kubernetes", "graphql", "redis", "terraform",
    }
    assert expected <= skills
    # The tier labels themselves must NOT leak in as skills.
    assert not ({"proficient", "experienced", "familiar"} & skills)


def test_gpa_does_not_leak_into_degree_or_field(claims):
    """'Cum. GPA: 3.85/4.0' sits right beside the degree; it must not bleed into it."""
    edu = claims["education"][0].value
    degree = (edu.get("degree") or "")
    assert "gpa" not in degree.lower()
    assert "3.85" not in degree and "/" not in degree
    # No 'field' is claimed here, but if one ever is, it must stay GPA-free too.
    field = (edu.get("field") or "")
    assert "gpa" not in field.lower() and "3.85" not in field


def test_reference_contacts_do_not_contaminate_candidate(claims):
    """THE adversarial case: reference people's emails/phones are not the candidate's."""
    emails = {c.value.lower() for c in claims["emails"]}
    assert emails == {"alex.rivera@example.com"}
    assert not (emails & REF_EMAILS)

    phone_digits = {_digits(c.value) for c in claims["phones"]}
    for ref in REF_PHONE_DIGITS:
        assert not any(ref in pd for pd in phone_digits)
    # The candidate's own number is still captured.
    assert any("4155550182" in pd for pd in phone_digits)
