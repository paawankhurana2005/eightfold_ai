"""Canonical data models and the intermediate *claim* type.

The transformer has exactly one internal source of truth: :class:`CandidateProfile`.
Every adapter produces :class:`FieldClaim` objects (one asserted value, plus where it
came from and how it was extracted); merge turns claims into a profile; the projection
layer turns a profile into whatever shape a runtime config asks for.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


# --------------------------------------------------------------------------- #
# Sources and extraction methods
# --------------------------------------------------------------------------- #
class Source:
    """Canonical source identifiers. Plain constants so provenance stays human-readable."""

    ATS_JSON = "ats_json"
    RECRUITER_CSV = "recruiter_csv"
    RESUME = "resume"
    GITHUB = "github"
    RECRUITER_NOTES = "recruiter_notes"

    ALL = (ATS_JSON, RECRUITER_CSV, RESUME, GITHUB, RECRUITER_NOTES)


class Method:
    """How a value was obtained — recorded in provenance and used by the confidence model.

    The ``FUZZY_METHODS`` set marks extraction/normalization that is inherently
    best-effort; the confidence model multiplies those by 0.9 (see ``confidence.py``).
    """

    DIRECT = "direct"        # read straight from a structured field (CSV cell)
    MAPPED = "mapped"        # ATS foreign key remapped to a canonical path
    API = "api"              # field from a structured API response (GitHub)
    REGEX = "regex"          # pulled out of prose with an anchored regex (resume/notes)
    HEURISTIC = "heuristic"  # resume section/header heuristics (experience/education)
    FUZZY = "fuzzy"          # fuzzy normalization (e.g. fuzzy country-name match)

    FUZZY_METHODS = frozenset({REGEX, HEURISTIC, FUZZY})


def is_fuzzy_method(method: str) -> bool:
    return method in Method.FUZZY_METHODS


# --------------------------------------------------------------------------- #
# Intermediate claim
# --------------------------------------------------------------------------- #
class FieldClaim(BaseModel):
    """A single asserted value for one canonical path, from one source.

    ``path`` uses the canonical path DSL (e.g. ``full_name``, ``emails``, ``phones``,
    ``location.country``, ``links.github``, ``skills``, ``experience``, ``education``).
    For list fields each element is its own claim. For object-list fields (skills,
    experience, education) ``value`` is a dict.
    """

    path: str
    value: Any
    source: str
    method: str
    fuzzy: bool = False  # OR-ed with method-based fuzziness by the confidence model

    def effective_fuzzy(self) -> bool:
        return self.fuzzy or is_fuzzy_method(self.method)


# --------------------------------------------------------------------------- #
# Canonical sub-models
# --------------------------------------------------------------------------- #
class Location(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None  # ISO-3166 alpha-2


class Links(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: list[str] = Field(default_factory=list)


class Skill(BaseModel):
    name: str
    confidence: float
    sources: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified_in_code(self) -> bool:
        """Read-only signal derived from existing corroboration — NOT a new scoring path.

        True iff this skill is corroborated by the candidate's public GitHub. A skill
        claimed in a resume but absent from the candidate's public code carries this flag
        rather than being silently trusted as equally strong. It only reads ``sources``
        (which merge already populates); it never feeds back into ``confidence``.
        """
        return Source.GITHUB in self.sources


class Experience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None    # YYYY-MM
    summary: Optional[str] = None


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None


class Provenance(BaseModel):
    field: str
    source: str
    method: str


class CandidateProfile(BaseModel):
    """The single internal canonical record. Source of truth for the projection layer."""

    candidate_id: str
    full_name: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    overall_confidence: float = 0.0

    # Internal-only: per-field confidence, never required by the default schema but
    # available to the projection layer and useful for debugging/explainability.
    field_confidence: dict[str, float] = Field(default_factory=dict)
