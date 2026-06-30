"""Build a JSON Schema from a projection config and validate the projected output.

The ``on_missing`` policy drives three distinct schema shapes (this is the heart of the
"validate against the requested schema" requirement):

    omit  -> field is NOT required; if absent, that's valid.
    null  -> field IS required and its type is NULLABLE (key present, value may be null).
    error -> field IS required and NON-NULL (a missing value fails loudly).
"""

from __future__ import annotations

from jsonschema import Draft202012Validator

from ..config import FieldSpec, ProjectionConfig

# requested type -> base JSON Schema fragment
_TYPE_MAP: dict[str, dict] = {
    "string": {"type": "string"},
    "string[]": {"type": "array", "items": {"type": "string"}},
    "number": {"type": "number"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "object": {"type": "object"},
    "object[]": {"type": "array", "items": {"type": "object"}},
    "any": {},
}


def _nullable(fragment: dict) -> dict:
    """Make a schema fragment accept null in addition to its declared type."""
    if "type" not in fragment:  # 'any' already accepts null
        return fragment
    base = fragment["type"]
    types = base if isinstance(base, list) else [base]
    if "null" not in types:
        types = types + ["null"]
    out = dict(fragment)
    out["type"] = types
    return out


def _field_schema(spec: FieldSpec, on_missing: str) -> dict:
    fragment = dict(_TYPE_MAP.get(spec.type, {}))
    if on_missing == "null":
        return _nullable(fragment)
    return fragment


def build_schema(config: ProjectionConfig) -> dict:
    properties: dict[str, dict] = {}
    required: list[str] = []

    for spec in config.fields:
        on_missing = spec.effective_on_missing(config.on_missing)
        properties[spec.path] = _field_schema(spec, on_missing)
        if on_missing in ("null", "error"):
            required.append(spec.path)

    # Toggled extras the projector may attach.
    if config.include_confidence:
        properties["overall_confidence"] = {"type": "number"}
    if config.include_provenance:
        properties["provenance"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "source": {"type": "string"},
                    "method": {"type": "string"},
                },
                "required": ["field", "source", "method"],
            },
        }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": sorted(set(required)),
        "additionalProperties": True,
    }


class SchemaValidationError(Exception):
    pass


def validate_output(output: dict, config: ProjectionConfig) -> dict:
    """Validate ``output`` against the schema generated from ``config``.

    Returns the schema (useful for tests/debugging). Raises SchemaValidationError with all
    messages joined if invalid.
    """
    schema = build_schema(config)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(output), key=lambda e: list(e.path))
    if errors:
        joined = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise SchemaValidationError(f"output failed schema validation: {joined}")
    return schema
