"""Runtime projection config: the shape the caller wants the output in.

This is the contract for the "configurable output" twist. The same engine emits the
default schema or any reshaped schema purely from one of these configs — no code changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ON_MISSING = ("null", "omit", "error")


class FieldSpec(BaseModel):
    """One output field.

    path      output key (supports dotted nesting, e.g. ``location.city``)
    from_     canonical source path (the "from" key); defaults to ``path``
    type      requested type: string | string[] | number | integer | boolean |
              object | object[] | any
    required  shorthand for on_missing="error"
    normalize per-field normalization: E164 | canonical | iso3166 | lower
    on_missing per-field override of the global policy: null | omit | error
    """

    model_config = ConfigDict(populate_by_name=True)

    path: str
    from_: Optional[str] = Field(default=None, alias="from")
    type: str = "any"
    required: bool = False
    normalize: Optional[str] = None
    on_missing: Optional[str] = None

    @field_validator("on_missing")
    @classmethod
    def _check_on_missing(cls, v):
        if v is not None and v not in ON_MISSING:
            raise ValueError(f"on_missing must be one of {ON_MISSING}, got {v!r}")
        return v

    @property
    def source_path(self) -> str:
        return self.from_ or self.path

    def effective_on_missing(self, global_default: str) -> str:
        if self.on_missing:
            return self.on_missing
        if self.required:
            return "error"
        return global_default


class ProjectionConfig(BaseModel):
    fields: list[FieldSpec]
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: str = "null"

    @field_validator("on_missing")
    @classmethod
    def _check_on_missing(cls, v):
        if v not in ON_MISSING:
            raise ValueError(f"on_missing must be one of {ON_MISSING}, got {v!r}")
        return v


def load_config(path: str | Path) -> ProjectionConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ProjectionConfig.model_validate(data)


def default_config() -> ProjectionConfig:
    """The full canonical/default output schema, expressed as a projection config.

    Even the default output goes through the projection layer — same engine, no special
    case — so the default and any custom config are produced by exactly one code path.
    """
    return ProjectionConfig.model_validate(
        {
            "fields": [
                {"path": "candidate_id", "type": "string", "required": True},
                {"path": "full_name", "type": "string"},
                {"path": "emails", "type": "string[]"},
                {"path": "phones", "type": "string[]"},
                {"path": "location", "type": "object"},
                {"path": "links", "type": "object"},
                {"path": "headline", "type": "string"},
                {"path": "years_experience", "type": "number"},
                # Each skill carries name, confidence, sources, and the derived
                # `verified_in_code` flag (True when "github" is among its sources) — a
                # read-only corroboration signal, not a new scoring path.
                {"path": "skills", "type": "object[]"},
                {"path": "experience", "type": "object[]"},
                {"path": "education", "type": "object[]"},
            ],
            "include_confidence": True,
            "include_provenance": True,
            "on_missing": "null",
        }
    )
