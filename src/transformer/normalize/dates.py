"""Date normalization to ``YYYY-MM``.

Accepts the common shapes that appear in resumes and ATS blobs. A value we cannot pin to
a specific year AND month is dropped — we do not invent a month (so a bare ``2019`` does
not silently become ``2019-01``). ``Present``/``Current`` resolves to ``None`` (ongoing).
"""

from __future__ import annotations

import re

from . import DROP, NormResult

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_PRESENT = {"present", "current", "now", "ongoing", "till date", "to date"}


def _fmt(year: int, month: int) -> NormResult:
    if not (1 <= month <= 12):
        return DROP
    if not (1900 <= year <= 2100):
        return DROP
    return NormResult(f"{year:04d}-{month:02d}", False)


def normalize_month(raw: object) -> NormResult:
    if raw is None:
        return DROP
    text = str(raw).strip().lower()
    if not text:
        return DROP
    if text in _PRESENT:
        return DROP  # ongoing -> caller leaves end as None

    # 2021-03 or 2021/3
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", text)
    if m:
        return _fmt(int(m.group(1)), int(m.group(2)))

    # 03/2021 or 3-2021
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text)
    if m:
        return _fmt(int(m.group(2)), int(m.group(1)))

    # March 2021 / Mar. 2021
    m = re.fullmatch(r"([a-z]{3,9})\.?\s+(\d{4})", text)
    if m and m.group(1) in _MONTHS:
        return _fmt(int(m.group(2)), _MONTHS[m.group(1)])

    # 2021 March
    m = re.fullmatch(r"(\d{4})\s+([a-z]{3,9})\.?", text)
    if m and m.group(2) in _MONTHS:
        return _fmt(int(m.group(1)), _MONTHS[m.group(2)])

    return DROP
