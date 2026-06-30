"""Independent oracle for Jane's profile — the COMPANION to test_gold_profile.py.

test_gold_profile.py compares against a snapshot of the pipeline's own output: it's a
strong *regression / determinism* guard, but a systematic bug present at snapshot time
would be baked into the gold file and still pass. This file is the antidote: every value
asserted below was derived **by hand from the raw source files**, NOT copied from a
pipeline run, so it checks *correctness* against a human-derived oracle.

Hand-derivation (from samples/inputs/jane-mcdonald/*):

* candidate_id — tier-1 identity is sha1("email|<best email>")[:12]. The best (only) email
  across all sources is ``jane.mcdonald@example.com`` →
  sha1("email|jane.mcdonald@example.com").hexdigest()[:12] = "996067f363f2" → "cand_996067f363f2".
  (Computed independently with hashlib below, not read from output.)

* full_name — ATS (trust 0.90) says "Jane Mcdonald"; CSV/GitHub/resume say "Jane McDonald".
  Highest trust wins → exact spelling "Jane Mcdonald". The lower-cased "Mc..." casing is the
  ATS value, which is the deliberate trust-winner over the more common "McDonald".

* phone — CSV has "+1 (415) 555-2671"; E.164 normalization → "+14155552671" (ATS already
  stores it that way). Single canonical phone.

* Python skill — appears in ATS skillSet, GitHub languages, recruiter notes prose, and the
  resume skills line = 4 sources. Confidence = base ATS 0.90 + 0.05*min(3 corrob,3)=+0.15
  = 1.05, clamped to the 0.99 ceiling. 4 distinct sources.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from transformer.config import default_config
from transformer.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
JANE = ROOT / "samples" / "inputs" / "jane-mcdonald"


def _jane_output() -> dict:
    return list(run_pipeline([JANE], default_config()))[0].output


def test_candidate_id_is_sha1_of_best_email():
    # Derived by hand: tier-1 id = sha1("email|<best email>")[:12], prefixed "cand_".
    expected = "cand_" + hashlib.sha1(
        b"email|jane.mcdonald@example.com"
    ).hexdigest()[:12]
    assert _jane_output()["candidate_id"] == expected


def test_full_name_is_ats_trust_winner():
    # ATS casing "Jane Mcdonald" (trust 0.90) beats "Jane McDonald" from the other sources.
    assert _jane_output()["full_name"] == "Jane Mcdonald"


def test_phone_is_e164_single():
    # CSV "+1 (415) 555-2671" -> E.164; deduped against ATS's identical value.
    assert _jane_output()["phones"] == ["+14155552671"]


def test_python_skill_corroborated_to_ceiling():
    skills = {s["name"]: s for s in _jane_output()["skills"]}
    py = skills["Python"]
    # 4 independent sources -> 0.90 + 0.15 corroboration = 1.05 -> clamped to 0.99 ceiling.
    assert py["confidence"] == 0.99
    assert set(py["sources"]) == {"ats_json", "github", "recruiter_notes", "resume"}


def test_verified_in_code_reflects_github_corroboration():
    # Derived signal, not a new scoring path: True iff "github" is among the skill's
    # sources. Python is in github.json (corroborated); PostgreSQL is resume-only.
    skills = {s["name"]: s for s in _jane_output()["skills"]}
    assert "github" in skills["Python"]["sources"]
    assert skills["Python"]["verified_in_code"] is True
    assert "github" not in skills["PostgreSQL"]["sources"]
    assert skills["PostgreSQL"]["verified_in_code"] is False
