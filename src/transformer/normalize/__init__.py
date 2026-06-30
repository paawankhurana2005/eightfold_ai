"""Normalization: small, pure, independently testable functions.

Every normalizer returns a :class:`NormResult`. A ``value`` of ``None`` means "could not
normalize honestly" — the caller drops the claim and the field stays empty. A normalizer
NEVER invents a value. ``fuzzy`` flags best-effort normalization (e.g. fuzzy country
match) so the confidence model can discount it.
"""

from __future__ import annotations

from typing import Any, NamedTuple


class NormResult(NamedTuple):
    value: Any
    fuzzy: bool = False


DROP = NormResult(None, False)


from .dates import normalize_month  # noqa: E402
from .emails import normalize_email  # noqa: E402
from .location import normalize_city, normalize_country, normalize_region  # noqa: E402
from .names import normalize_name  # noqa: E402
from .phones import normalize_phone  # noqa: E402
from .skills import canonicalize_skill  # noqa: E402

__all__ = [
    "NormResult",
    "DROP",
    "normalize_month",
    "normalize_email",
    "normalize_city",
    "normalize_country",
    "normalize_region",
    "normalize_name",
    "normalize_phone",
    "canonicalize_skill",
]
