"""Tests for the projection layer: path DSL, remap, normalize, toggles, on_missing schema."""

from __future__ import annotations

import pytest

from transformer.config import ProjectionConfig
from transformer.models import CandidateProfile, Location, Provenance, Skill
from transformer.projection import (
    MissingFieldError,
    SchemaValidationError,
    build_schema,
    project,
    resolve,
)


def make_profile(**over) -> CandidateProfile:
    base = dict(
        candidate_id="cand_1",
        full_name="Jane",
        emails=["jane@x.com"],
        phones=["+14155552671"],
        location=Location(city="SF", country="US"),
        skills=[Skill(name="Python", confidence=0.99, sources=["ats_json"])],
        provenance=[Provenance(field="full_name", source="ats_json", method="mapped")],
        overall_confidence=0.9,
    )
    base.update(over)
    return CandidateProfile(**base)


class TestResolver:
    def test_index(self):
        assert resolve({"emails": ["a", "b"]}, "emails[0]") == (True, "a")

    def test_wildcard(self):
        data = {"skills": [{"name": "Python"}, {"name": "Go"}]}
        assert resolve(data, "skills[].name") == (True, ["Python", "Go"])

    def test_dotted(self):
        assert resolve({"location": {"city": "SF"}}, "location.city") == (True, "SF")

    def test_out_of_range_is_not_found(self):
        assert resolve({"phones": []}, "phones[0]") == (False, None)


class TestProjection:
    def test_remap_from_path(self):
        cfg = ProjectionConfig.model_validate(
            {"fields": [{"path": "primary_email", "from": "emails[0]", "type": "string"}],
             "include_confidence": False, "include_provenance": False}
        )
        out = project(make_profile(), cfg)
        assert out == {"primary_email": "jane@x.com"}

    def test_normalize_canonical_on_projection(self):
        prof = make_profile(skills=[Skill(name="js", confidence=0.5, sources=["github"])])
        cfg = ProjectionConfig.model_validate(
            {"fields": [{"path": "skills", "from": "skills[].name", "type": "string[]",
                         "normalize": "canonical"}],
             "include_confidence": False, "include_provenance": False}
        )
        assert project(prof, cfg)["skills"] == ["JavaScript"]

    def test_confidence_toggle_off_strips_skill_confidence(self):
        cfg = ProjectionConfig.model_validate(
            {"fields": [{"path": "skills", "type": "object[]"}],
             "include_confidence": False, "include_provenance": True}
        )
        out = project(make_profile(), cfg)
        assert "overall_confidence" not in out
        assert all("confidence" not in s for s in out["skills"])

    def test_provenance_toggle_on(self):
        cfg = ProjectionConfig.model_validate(
            {"fields": [{"path": "full_name", "type": "string"}],
             "include_confidence": False, "include_provenance": True}
        )
        out = project(make_profile(), cfg)
        assert out["provenance"][0]["field"] == "full_name"


class TestOnMissingSchemaPaths:
    """The three distinct schema-generation paths driven by on_missing."""

    def _cfg(self, on_missing):
        return ProjectionConfig.model_validate(
            {"fields": [{"path": "headline", "from": "headline", "type": "string",
                         "on_missing": on_missing}],
             "include_confidence": False, "include_provenance": False}
        )

    def test_omit_field_absent_and_not_required(self):
        cfg = self._cfg("omit")
        out = project(make_profile(headline=None), cfg)  # headline missing
        assert "headline" not in out
        assert "headline" not in build_schema(cfg)["required"]

    def test_null_field_present_nullable_and_required(self):
        cfg = self._cfg("null")
        out = project(make_profile(headline=None), cfg)
        assert out["headline"] is None
        schema = build_schema(cfg)
        assert "headline" in schema["required"]
        assert "null" in schema["properties"]["headline"]["type"]

    def test_error_field_required_nonnull_and_raises(self):
        cfg = self._cfg("error")
        schema = build_schema(cfg)
        assert "headline" in schema["required"]
        assert schema["properties"]["headline"]["type"] == "string"  # non-null
        with pytest.raises(MissingFieldError):
            project(make_profile(headline=None), cfg)


def test_validation_catches_type_mismatch():
    # required string field present as the wrong type should fail schema validation.
    cfg = ProjectionConfig.model_validate(
        {"fields": [{"path": "years_experience", "type": "string", "required": True}],
         "include_confidence": False, "include_provenance": False}
    )
    # years_experience is a number in the canonical record -> violates "string".
    with pytest.raises(SchemaValidationError):
        project(make_profile(years_experience=9.0), cfg)
