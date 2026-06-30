"""Projection layer: project a canonical profile into a config-defined output shape."""

from __future__ import annotations

from .path_resolver import resolve
from .projector import MissingFieldError, project
from .validator import SchemaValidationError, build_schema, validate_output

__all__ = [
    "resolve",
    "project",
    "MissingFieldError",
    "build_schema",
    "validate_output",
    "SchemaValidationError",
]
