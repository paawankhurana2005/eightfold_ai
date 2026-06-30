"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from transformer.models import FieldClaim

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture
def samples_dir() -> Path:
    return SAMPLES


def claim(path: str, value, source: str, method: str = "direct", fuzzy: bool = False) -> FieldClaim:
    """Concise FieldClaim builder for tests."""
    return FieldClaim(path=path, value=value, source=source, method=method, fuzzy=fuzzy)
