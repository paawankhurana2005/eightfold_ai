"""Recruiter CSV export adapter.

Structured rows with columns: name, email, phone, current_company, title. Each file is
expected to describe a single candidate (one data row); extra rows are ignored with a
warning. Column matching is case-insensitive and tolerant of minor header variants.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import Method
from .base import ExtractResult, SourceAdapter

# header variants -> our internal key
_HEADERS = {
    "name": "name", "full_name": "name", "candidate": "name", "candidate_name": "name",
    "email": "email", "email_address": "email", "e-mail": "email",
    "phone": "phone", "phone_number": "phone", "mobile": "phone", "cell": "phone",
    "current_company": "company", "company": "company", "employer": "company",
    "title": "title", "job_title": "title", "role": "title", "position": "title",
}


class RecruiterCsvAdapter(SourceAdapter):
    source = "recruiter_csv"

    def extract(self, path: Path) -> ExtractResult:
        result = ExtractResult()
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        if not text.strip():
            result.warnings.append(f"{self.source}: empty file {path}")
            return result

        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames:
            result.warnings.append(f"{self.source}: no header row in {path}")
            return result

        # Map actual headers to internal keys once.
        colmap = {}
        for raw_header in reader.fieldnames:
            key = _HEADERS.get((raw_header or "").strip().lower())
            if key:
                colmap[raw_header] = key

        rows = list(reader)
        if not rows:
            result.warnings.append(f"{self.source}: header but no data rows in {path}")
            return result
        if len(rows) > 1:
            result.warnings.append(
                f"{self.source}: {len(rows)} rows in {path}; using the first only"
            )

        row = rows[0]
        company = title = None
        for raw_header, key in colmap.items():
            value = (row.get(raw_header) or "").strip()
            if not value:
                continue
            if key == "name":
                result.claims.append(self._claim("full_name", value, Method.DIRECT))
            elif key == "email":
                result.claims.append(self._claim("emails", value, Method.DIRECT))
            elif key == "phone":
                result.claims.append(self._claim("phones", value, Method.DIRECT))
            elif key == "company":
                company = value
            elif key == "title":
                title = value

        # current_company + title form a single (current) experience entry.
        if company or title:
            result.claims.append(
                self._claim(
                    "experience",
                    {"company": company, "title": title, "start": None, "end": None,
                     "summary": None},
                    Method.DIRECT,
                )
            )
        return result
