"""Tests for the 3-tier candidate_id fallback chain and the no-dedupe stance."""

from __future__ import annotations

from conftest import claim

from transformer.merge import merge


def _id(claims, hint="folder"):
    return merge(claims, identity_hint=hint).candidate_id


def test_tier_a_email_drives_id():
    # With an email present, the id depends on the email and NOT on the name.
    base = [claim("emails", "a@x.com", "ats_json", "mapped")]
    id1 = _id(base + [claim("full_name", "Jane A", "ats_json", "mapped")])
    id2 = _id(base + [claim("full_name", "Totally Different", "recruiter_csv", "direct")])
    assert id1 == id2


def test_tier_b_name_plus_phone_when_no_email():
    claims = [
        claim("full_name", "Liang Wei", "ats_json", "mapped"),
        claim("phones", "+31206241111", "ats_json", "mapped"),
    ]
    # Deterministic and stable across runs.
    assert _id(claims) == _id(list(reversed(claims)))
    # Changing the phone changes the identity (it is part of the key).
    other = [claim("full_name", "Liang Wei", "ats_json", "mapped"),
             claim("phones", "+31206249999", "ats_json", "mapped")]
    assert _id(claims) != _id(other)


def test_tier_c_name_plus_source_when_no_email_or_phone():
    claims = [claim("full_name", "Marco Rossi", "resume", "heuristic")]
    # Same name, different source-file identity -> different records (kept separate).
    assert _id(claims, hint="folderA") != _id(claims, hint="folderB")


def test_zero_identifiers_are_deterministic_but_not_merged():
    # No email, name, or phone — only a skill. We still produce a stable id, but two
    # different anonymous candidates do NOT collapse together.
    a = [claim("skills", "Python", "recruiter_notes", "regex")]
    b = [claim("skills", "Java", "recruiter_notes", "regex")]
    assert _id(a, hint=None) == _id(a, hint=None)  # deterministic
    assert _id(a, hint=None) != _id(b, hint=None)  # not merged
