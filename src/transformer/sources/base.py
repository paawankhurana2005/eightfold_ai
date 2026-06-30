"""Source-adapter contract.

Every adapter takes a single input (usually a file path) and returns an
:class:`ExtractResult` of RAW claims plus any warnings. The cardinal rule: **an adapter
never raises on bad input.** A missing, empty, or malformed source yields an empty claim
list and a captured warning, so one garbage source can never crash the run.

Normalization is intentionally NOT done here — adapters only extract raw values and
record where/how they got them. The normalize stage handles canonical formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models import FieldClaim


@dataclass
class ExtractResult:
    claims: list[FieldClaim] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SourceAdapter:
    source: str = "base"

    def extract(self, path: Path) -> ExtractResult:  # pragma: no cover - interface
        raise NotImplementedError

    # Convenience for subclasses: wrap extraction so nothing escapes as an exception.
    def safe_extract(self, path: Path) -> ExtractResult:
        try:
            return self.extract(path)
        except Exception as exc:  # noqa: BLE001 - robustness is the whole point
            return ExtractResult(
                claims=[],
                warnings=[f"{self.source}: failed to read {path} ({exc.__class__.__name__}: {exc})"],
            )

    def _claim(self, path: str, value: object, method: str) -> FieldClaim:
        return FieldClaim(path=path, value=value, source=self.source, method=method)
