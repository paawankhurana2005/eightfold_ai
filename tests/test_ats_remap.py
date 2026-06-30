"""Tests for the explicit ATS foreign-key -> canonical-path remapping."""

from __future__ import annotations

import json

from transformer.sources import AtsJsonAdapter


def _paths(claims):
    return {(c.path, c.method) for c in claims}


def test_foreign_keys_mapped_to_canonical(tmp_path):
    blob = {
        "candidateName": "Asha Rao",
        "emailAddress": "asha@x.com",
        "mobile": "+14155550000",
        "locationCity": "Austin",
        "locationCountry": "USA",
        "skillSet": ["Python"],
        "workHistory": [{"employer": "Acme", "role": "SWE", "startDate": "2020-01"}],
        "education": [{"school": "UT", "degree": "BS", "gradYear": 2018}],
    }
    f = tmp_path / "ats.json"
    f.write_text(json.dumps(blob))
    res = AtsJsonAdapter().extract(f)
    paths = {c.path for c in res.claims}
    assert {"full_name", "emails", "phones", "location.city", "location.country",
            "skills", "experience", "education"} <= paths
    # Everything from the ATS is recorded as a MAPPED method (traceable remap).
    assert all(c.method == "mapped" for c in res.claims)


def test_unmapped_fields_ignored_and_logged(tmp_path):
    blob = {"candidateName": "Asha", "internalAtsId": "X-1", "recruiterRating": "strong"}
    f = tmp_path / "ats.json"
    f.write_text(json.dumps(blob))
    res = AtsJsonAdapter().extract(f)
    # internalAtsId / recruiterRating are NOT guessed into any canonical field.
    assert {c.path for c in res.claims} == {"full_name"}
    assert any("internalAtsId" in w and "recruiterRating" in w for w in res.warnings)
