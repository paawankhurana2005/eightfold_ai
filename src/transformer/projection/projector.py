"""Projection layer: canonical CandidateProfile -> the config's requested shape.

This is the strict wall between our internal record and any output schema. The projector
only reads canonical values via the path DSL, applies per-field normalization, honors the
missing-value policy, toggles provenance/confidence, and validates the result.
"""

from __future__ import annotations

from typing import Any

from ..config import ProjectionConfig
from ..models import CandidateProfile
from ..normalize import canonicalize_skill, normalize_country, normalize_phone
from .path_resolver import resolve
from .validator import validate_output


class MissingFieldError(Exception):
    """Raised when a required field (on_missing='error') resolves to nothing."""


def _empty(value: Any) -> bool:
    """Used for filtering normalized list items: drops None / blank entries."""
    return value is None or value == "" or value == [] or value == {}


def _missing(value: Any) -> bool:
    """Presence test for projection. An empty list/dict is a real, honestly-empty value
    (we looked and found none) and is kept; only None / blank / not-found is 'missing'."""
    return value is None or value == ""


def _apply_one(name: str, value: Any) -> Any:
    if name == "E164":
        return normalize_phone(value).value
    if name == "canonical":
        return canonicalize_skill(value).value
    if name == "iso3166":
        return normalize_country(value).value
    if name == "lower":
        return str(value).lower()
    return value  # unknown normalizer: pass through (validation will still run)


def _normalize(name: str, value: Any) -> Any:
    if isinstance(value, list):
        out = [_apply_one(name, v) for v in value]
        return [v for v in out if not _empty(v)]
    return _apply_one(name, value)


def _set_path(out: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    node = out
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _strip_keys(obj: Any, keys: set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_keys(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [_strip_keys(v, keys) for v in obj]
    return obj


def project(profile: CandidateProfile, config: ProjectionConfig, validate: bool = True) -> dict:
    canonical = profile.model_dump(exclude={"field_confidence"})
    out: dict = {}

    for spec in config.fields:
        found, raw = resolve(canonical, spec.source_path)
        value = None
        present = False
        if found and not _missing(raw):
            value = _normalize(spec.normalize, raw) if spec.normalize else raw
            present = not _missing(value)

        if present:
            _set_path(out, spec.path, value)
            continue

        policy = spec.effective_on_missing(config.on_missing)
        if policy == "omit":
            continue
        if policy == "null":
            _set_path(out, spec.path, None)
            continue
        raise MissingFieldError(
            f"required field {spec.path!r} (from {spec.source_path!r}) is missing"
        )

    # Toggle confidence: drop per-skill confidence and the overall score when off.
    if not config.include_confidence:
        out = _strip_keys(out, {"confidence"})
    else:
        out["overall_confidence"] = profile.overall_confidence

    # Toggle provenance: per-skill sources are provenance too.
    if not config.include_provenance:
        out = _strip_keys(out, {"sources"})
    else:
        out["provenance"] = [p.model_dump() for p in profile.provenance]

    if validate:
        validate_output(out, config)
    return out
