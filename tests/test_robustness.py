"""A missing or garbage source must not crash the run; unknowns become null, not invented."""

from __future__ import annotations

from pathlib import Path

from transformer.config import default_config
from transformer.pipeline import process_candidate, run_pipeline
from transformer.sources import AtsJsonAdapter, RecruiterCsvAdapter


def test_malformed_json_does_not_crash(tmp_path):
    f = tmp_path / "ats.json"
    f.write_text('{ "candidateName": "X", "emailAddress":')  # truncated
    res = AtsJsonAdapter().safe_extract(f)
    assert res.claims == [] and any("invalid JSON" in w for w in res.warnings)


def test_empty_csv_does_not_crash(tmp_path):
    f = tmp_path / "recruiter.csv"
    f.write_text("")
    res = RecruiterCsvAdapter().safe_extract(f)
    assert res.claims == [] and res.warnings


def test_garbage_candidate_still_degrades_gracefully(tmp_path):
    # malformed ATS + empty CSV, but a usable notes file -> profile still produced.
    (tmp_path / "ats.json").write_text('{ "candidateName":')
    (tmp_path / "recruiter.csv").write_text("")
    (tmp_path / "notes.txt").write_text(
        "Proficient in Java and Spring. Email x@y.com."
    )
    profile, warnings = process_candidate("c", sorted(tmp_path.iterdir()), live=False, cache_dir=None)
    assert profile.emails == ["x@y.com"]
    assert {s.name for s in profile.skills} == {"Java", "Spring"}
    assert len(warnings) >= 2  # the two bad sources were reported


def test_unknown_values_stay_null_never_invented(tmp_path):
    # A source with only a name -> no phone/location is fabricated.
    (tmp_path / "ats.json").write_text('{"candidateName": "Solo Person"}')
    profile, _ = process_candidate("c", [tmp_path / "ats.json"], live=False, cache_dir=None)
    assert profile.full_name == "Solo Person"
    assert profile.phones == []
    assert profile.location.country is None


def test_end_to_end_on_samples_is_schema_valid():
    samples = Path(__file__).resolve().parent.parent / "samples" / "inputs"
    results = list(run_pipeline([samples], default_config()))
    assert len(results) == 4  # jane, liang, marco, alex (adversarial resume)
    assert all(r.output is not None for r in results)  # all validated successfully
