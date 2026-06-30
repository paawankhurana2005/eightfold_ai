"""Gold-profile comparison: the full default projection for Jane (the multi-source,
conflicting-value edge case) must match a committed gold file exactly.

This is the strongest determinism + regression guard: it pins identity, conflict
resolution (ATS casing winning), unioned skills with corroborated confidence, deduped
education, and full provenance — all in one assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

from transformer.config import default_config
from transformer.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
GOLD = Path(__file__).resolve().parent / "fixtures" / "gold_jane.json"


def test_jane_matches_gold_profile():
    results = list(run_pipeline([ROOT / "samples" / "inputs" / "jane-mcdonald"], default_config()))
    produced = results[0].output
    expected = json.loads(GOLD.read_text(encoding="utf-8"))
    assert produced == expected
