"""A tiny path DSL for reading from the canonical record.

Supported forms:
    full_name            scalar
    location.city        dotted
    emails[0]            list index
    skills[].name        wildcard collect over a list -> list of values
    experience[].company wildcard collect over object list

``resolve`` returns ``(found, value)``. ``found`` is False when any segment is absent or
an index is out of range — the projector turns that into the configured missing policy.
"""

from __future__ import annotations

import re
from typing import Any

_SEGMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)?(?:\[(\d+)\])?(\[\])?$")


class _Token:
    __slots__ = ("name", "index", "wildcard")

    def __init__(self, name, index, wildcard):
        self.name = name
        self.index = index
        self.wildcard = wildcard


def _tokenize(path: str) -> list[_Token]:
    tokens = []
    for piece in path.split("."):
        m = _SEGMENT.match(piece)
        if not m:
            raise ValueError(f"invalid path segment: {piece!r} in {path!r}")
        name, index, wildcard = m.group(1), m.group(2), m.group(3)
        tokens.append(_Token(name, int(index) if index is not None else None, bool(wildcard)))
    return tokens


def _walk(node: Any, tokens: list[_Token]) -> tuple[bool, Any]:
    if not tokens:
        return True, node
    tok = tokens[0]

    if tok.name:
        if not isinstance(node, dict) or tok.name not in node:
            return False, None
        node = node[tok.name]

    if tok.wildcard:
        if not isinstance(node, list):
            return False, None
        collected = []
        for item in node:
            found, value = _walk(item, tokens[1:])
            if found and value is not None:
                collected.append(value)
        return True, collected

    if tok.index is not None:
        if not isinstance(node, list) or tok.index >= len(node):
            return False, None
        node = node[tok.index]

    return _walk(node, tokens[1:])


def resolve(data: dict, path: str) -> tuple[bool, Any]:
    return _walk(data, _tokenize(path))
