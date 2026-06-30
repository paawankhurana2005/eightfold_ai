"""End-to-end pipeline tests over the committed sample inputs."""

from __future__ import annotations

from pathlib import Path

from transformer.config import default_config, load_config
from transformer.pipeline import run_pipeline

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def _by_name(results):
    return {r.profile.full_name: r for r in results}


def test_multi_source_merge_and_corroboration():
    results = list(run_pipeline([SAMPLES / "inputs"], default_config()))
    jane = _by_name(results)["Jane Mcdonald"]  # ATS casing wins on trust
    out = jane.output
    assert out["emails"] == ["jane.mcdonald@example.com"]
    assert out["phones"] == ["+14155552671"]
    assert out["location"]["country"] == "US"
    python = next(s for s in out["skills"] if s["name"] == "Python")
    assert python["confidence"] == 0.99
    assert set(python["sources"]) == {"ats_json", "github", "recruiter_notes", "resume"}


def test_name_plus_phone_identity_for_emailless_candidate():
    results = list(run_pipeline([SAMPLES / "inputs"], default_config()))
    liang = _by_name(results)["Liang Wei"]
    assert liang.output["emails"] == []          # no email anywhere
    assert liang.output["phones"] == ["+31206241111"]
    assert liang.output["location"]["country"] == "NL"  # fuzzy-matched, discounted


def test_robust_candidate_saved_by_resume():
    results = list(run_pipeline([SAMPLES / "inputs"], default_config()))
    marco = _by_name(results)["Marco Rossi"]
    assert marco.output is not None  # malformed ATS + empty CSV did not break it
    assert marco.output["emails"] == ["marco.rossi@example.com"]


def test_custom_config_reshapes_same_engine():
    cfg = load_config(SAMPLES / "configs" / "custom_recruiter_summary.json")
    results = list(run_pipeline([SAMPLES / "inputs" / "jane-mcdonald"], cfg))
    out = results[0].output
    assert set(out) >= {"primary_email", "phone", "current_title", "current_company"}
    assert out["primary_email"] == "jane.mcdonald@example.com"


def test_deterministic_across_runs():
    a = [r.output for r in run_pipeline([SAMPLES / "inputs"], default_config())]
    b = [r.output for r in run_pipeline([SAMPLES / "inputs"], default_config())]
    assert a == b
