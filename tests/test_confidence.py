"""Tests for the concrete confidence math."""

from __future__ import annotations

from transformer import confidence as c


def test_trust_table_values():
    assert c.base_trust("ats_json") == 0.90
    assert c.base_trust("recruiter_csv") == 0.85
    assert c.base_trust("resume") == 0.60
    assert c.base_trust("github") == 0.50
    assert c.base_trust("recruiter_notes") == 0.35


def test_corroboration_step_and_cap():
    # +0.05 per corroboration, capped at +0.15 (<=3 counted).
    assert c.field_confidence("resume", 1, False) == 0.65
    assert c.field_confidence("resume", 3, False) == 0.75
    assert c.field_confidence("resume", 9, False) == 0.75  # cap


def test_fuzzy_multiplier():
    assert c.field_confidence("resume", 0, True) == round(0.60 * 0.9, 4)  # 0.54


def test_clamp_never_reaches_one():
    # 0.90 + 0.15 = 1.05 -> clamped to 0.99 (nothing is certain).
    assert c.field_confidence("ats_json", 3, False) == 0.99


def test_single_low_trust_source_capped_at_base():
    # notes-only, no corroboration -> exactly base trust.
    assert c.field_confidence("recruiter_notes", 0, False) == 0.35


def test_overall_is_importance_weighted():
    # identity (full_name w=3) dominates a low-weight field (headline w=1).
    field_conf = {"full_name": 0.9, "headline": 0.5}
    assert c.overall_confidence(field_conf) == round((3 * 0.9 + 1 * 0.5) / 4, 4)


def test_overall_empty_is_zero():
    assert c.overall_confidence({}) == 0.0
