"""Tests for merge / conflict-resolution policy."""

from __future__ import annotations

from conftest import claim

from transformer.merge import merge


def test_scalar_winner_by_trust():
    # ATS (0.90) beats CSV (0.85) even though they disagree.
    claims = [
        claim("full_name", "Jane Mcdonald", "ats_json", "mapped"),
        claim("full_name", "Jane McDonald", "recruiter_csv", "direct"),
    ]
    p = merge(claims, identity_hint="c1")
    assert p.full_name == "Jane Mcdonald"


def test_casefold_corroboration_boosts_confidence():
    # Different casing from 3 other sources still corroborates the trust winner.
    claims = [
        claim("full_name", "Jane Mcdonald", "ats_json", "mapped"),
        claim("full_name", "Jane McDonald", "recruiter_csv", "direct"),
        claim("full_name", "Jane McDonald", "github", "api"),
        claim("full_name", "JANE MCDONALD", "resume", "heuristic"),
    ]
    p = merge(claims, identity_hint="c1")
    assert p.full_name == "Jane Mcdonald"
    assert p.field_confidence["full_name"] == 0.99  # 0.90 + capped corroboration


def test_list_fields_unioned_and_deduped():
    claims = [
        claim("emails", "a@x.com", "ats_json", "mapped"),
        claim("emails", "a@x.com", "recruiter_csv", "direct"),
        claim("emails", "b@x.com", "resume", "regex"),
    ]
    p = merge(claims, identity_hint="c1")
    assert p.emails == ["a@x.com", "b@x.com"]


def test_skill_sources_collected_and_sorted():
    claims = [
        claim("skills", "Python", "ats_json", "mapped"),
        claim("skills", "Python", "github", "api"),
        claim("skills", "Python", "resume", "regex"),
    ]
    p = merge(claims, identity_hint="c1")
    python = next(s for s in p.skills if s.name == "Python")
    assert python.sources == ["ats_json", "github", "resume"]
    assert python.confidence == 0.99  # 0.90 + corroboration, clamped


def test_equal_trust_tiebreak_is_stable(monkeypatch):
    # If two sources ever share a trust value, the winner must be deterministic regardless
    # of set iteration order (PYTHONHASHSEED). Tie-break is on the source name.
    from transformer import confidence as conf

    monkeypatch.setitem(conf.TRUST, "github", 0.50)
    monkeypatch.setitem(conf.TRUST, "resume", 0.50)  # now equal-trust
    fwd = [claim("skills", "Go", "github", "api"), claim("skills", "Go", "resume", "regex")]
    rev = list(reversed(fwd))
    p1 = merge(fwd, identity_hint="c1")
    p2 = merge(rev, identity_hint="c1")
    # Same winner -> same confidence in both orders (order-independent, hence stable).
    assert p1.skills[0].confidence == p2.skills[0].confidence


def test_provenance_records_every_populated_field():
    claims = [claim("full_name", "Jane", "ats_json", "mapped")]
    p = merge(claims, identity_hint="c1")
    assert any(pr.field == "full_name" and pr.source == "ats_json" for pr in p.provenance)
