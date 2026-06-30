"""Merge / dedupe: normalized claims -> one canonical CandidateProfile.

Conflict policy: scalar winners by source trust (tie-broken by completeness, then stable
source order); multi-valued fields unioned and de-duped; provenance and confidence
recorded for every populated field. Identity uses a 3-tier fallback chain so candidate_id
is deterministic and merges stay conservative.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict, defaultdict

from . import confidence as conf
from .models import (
    CandidateProfile,
    Education,
    Experience,
    Links,
    Location,
    Provenance,
    Skill,
)

_SCALAR_PATHS = [
    "full_name",
    "headline",
    "years_experience",
    "location.city",
    "location.region",
    "location.country",
    "links.linkedin",
    "links.github",
    "links.portfolio",
]
_LIST_PATHS = ["emails", "phones", "links.other"]

# canonical path -> field-importance group used for the overall confidence weighting
_GROUP = {
    "full_name": "full_name",
    "headline": "headline",
    "years_experience": "years_experience",
    "location.city": "location",
    "location.region": "location",
    "location.country": "location",
    "links.linkedin": "links",
    "links.github": "links",
    "links.portfolio": "links",
    "links.other": "links",
    "emails": "emails",
    "phones": "phones",
    "skills": "skills",
    "experience": "experience",
    "education": "education",
}


def _hash(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"cand_{digest}"


def _eq(a: object, b: object) -> bool:
    return str(a).casefold() == str(b).casefold()


class _Merger:
    def __init__(self, claims, identity_hint: str | None):
        self.by_path: dict[str, list] = defaultdict(list)
        for c in claims:
            self.by_path[c.path].append(c)
        self.identity_hint = identity_hint
        self.provenance: set[tuple[str, str, str]] = set()
        self.group_confs: dict[str, list[float]] = defaultdict(list)

    # --- identity -------------------------------------------------------------------- #
    def candidate_id(self) -> tuple[str, str]:
        emails = sorted({c.value for c in self.by_path.get("emails", [])})
        if emails:
            return _hash("email", emails[0]), "email"
        name = self._best_name()
        phones = sorted({c.value for c in self.by_path.get("phones", [])})
        if name and phones:
            return _hash("name+phone", name.lower(), phones[0]), "name+phone"
        if name and self.identity_hint:
            return _hash("name+source", name.lower(), self.identity_hint), "name+source"
        if self.identity_hint:
            return _hash("source", self.identity_hint), "source-only"
        # Zero matchable identifiers: cross-source dedupe is NOT attempted; the record
        # stays standalone, keyed by a stable hash of its own claims.
        signature = repr(sorted((c.path, str(c.value)) for c in _flatten(self.by_path)))
        return _hash("anon", signature), "none"

    def _best_name(self) -> str | None:
        claims = self.by_path.get("full_name", [])
        if not claims:
            return None
        return self._winner(claims).value

    # --- generic helpers ------------------------------------------------------------- #
    @staticmethod
    def _winner(claims):
        # Highest trust, then most complete value, then stable source order.
        return sorted(
            claims,
            key=lambda c: (-conf.rank(c.source), -len(str(c.value)), c.source),
        )[0]

    def _record_prov(self, field: str, source: str, method: str) -> None:
        self.provenance.add((field, source, method))

    # --- scalar fields --------------------------------------------------------------- #
    def merge_scalar(self, path: str):
        claims = self.by_path.get(path)
        if not claims:
            return None
        winner = self._winner(claims)
        # Corroboration is case-insensitive: a different source asserting the same value
        # in different casing (e.g. "Jane McDonald" vs "Jane Mcdonald") still corroborates
        # the trust-ranked winner, even though we keep the winner's exact spelling.
        agreeing = {c.source for c in claims if _eq(c.value, winner.value)}
        corro = len(agreeing) - 1
        confidence = conf.field_confidence(winner.source, corro, winner.effective_fuzzy())
        self.group_confs[_GROUP[path]].append(confidence)
        self._record_prov(path, winner.source, winner.method)
        return winner.value

    # --- list-of-scalar fields ------------------------------------------------------- #
    def merge_list(self, path: str) -> list[str]:
        claims = self.by_path.get(path)
        if not claims:
            return []
        val_sources: dict[str, set[str]] = defaultdict(set)
        for c in claims:
            val_sources[c.value].add(c.source)
            self._record_prov(path, c.source, c.method)
        values = sorted(val_sources)
        # Confidence from the most-corroborated value.
        best = max(values, key=lambda v: (len(val_sources[v]), max(conf.rank(s) for s in val_sources[v])))
        # Tie-break on the source name so equal-trust sources resolve deterministically
        # regardless of set iteration order (PYTHONHASHSEED).
        winner_source = max(val_sources[best], key=lambda s: (conf.rank(s), s))
        corro = len(val_sources[best]) - 1
        fuzzy = all(c.effective_fuzzy() for c in claims if c.value == best)
        confidence = conf.field_confidence(winner_source, corro, fuzzy)
        self.group_confs[_GROUP[path]].append(confidence)
        return values

    # --- skills ---------------------------------------------------------------------- #
    def merge_skills(self) -> list[Skill]:
        claims = self.by_path.get("skills")
        if not claims:
            return []
        by_name: dict[str, list] = defaultdict(list)
        for c in claims:
            by_name[c.value].append(c)
        skills = []
        for name in sorted(by_name):
            group = by_name[name]
            sources = sorted({c.source for c in group})
            corro = len(sources) - 1
            fuzzy = all(c.effective_fuzzy() for c in group)
            winner = max(sources, key=lambda s: (conf.rank(s), s))
            confidence = conf.field_confidence(winner, corro, fuzzy)
            skills.append(Skill(name=name, confidence=confidence, sources=sources))
            for c in group:
                self._record_prov("skills", c.source, c.method)
        if skills:
            self.group_confs["skills"].append(
                round(sum(s.confidence for s in skills) / len(skills), 4)
            )
        return skills

    # --- object lists (experience / education) --------------------------------------- #
    def merge_objects(self, path: str, key_fields, all_fields):
        claims = self.by_path.get(path)
        if not claims:
            return []
        groups: "OrderedDict[tuple, list]" = OrderedDict()
        for c in claims:
            key = tuple((str(c.value.get(f, "")).strip().lower()) for f in key_fields)
            groups.setdefault(key, []).append(c)

        merged_rows = []
        for group in groups.values():
            ordered = sorted(group, key=lambda c: -conf.rank(c.source))
            merged: dict = {}
            for field in all_fields:
                for c in ordered:
                    if c.value.get(field) is not None:
                        merged[field] = c.value[field]
                        break
            sources = sorted({c.source for c in group})
            corro = len(sources) - 1
            fuzzy = all(c.effective_fuzzy() for c in group)
            confidence = conf.field_confidence(ordered[0].source, corro, fuzzy)
            for c in group:
                self._record_prov(path, c.source, c.method)
            merged_rows.append((merged, confidence))

        if merged_rows:
            self.group_confs[path].append(
                round(sum(c for _, c in merged_rows) / len(merged_rows), 4)
            )
        return [m for m, _ in merged_rows]


def _flatten(by_path):
    for claims in by_path.values():
        yield from claims


def merge(claims, identity_hint: str | None = None) -> CandidateProfile:
    m = _Merger(claims, identity_hint)
    candidate_id, _id_tier = m.candidate_id()

    full_name = m.merge_scalar("full_name")
    headline = m.merge_scalar("headline")
    years = m.merge_scalar("years_experience")
    if years is not None and float(years).is_integer():
        years = int(years)

    location = Location(
        city=m.merge_scalar("location.city"),
        region=m.merge_scalar("location.region"),
        country=m.merge_scalar("location.country"),
    )
    links = Links(
        linkedin=m.merge_scalar("links.linkedin"),
        github=m.merge_scalar("links.github"),
        portfolio=m.merge_scalar("links.portfolio"),
        other=m.merge_list("links.other"),
    )
    emails = m.merge_list("emails")
    phones = m.merge_list("phones")
    skills = m.merge_skills()
    experience_rows = m.merge_objects(
        "experience", ("company", "title"), ("company", "title", "start", "end", "summary")
    )
    education_rows = m.merge_objects(
        "education", ("end_year", "degree"), ("institution", "degree", "field", "end_year")
    )

    experience = sorted(
        (Experience(**row) for row in experience_rows),
        key=lambda e: (e.start or "", e.company or ""),
        reverse=True,
    )
    education = sorted(
        (Education(**row) for row in education_rows),
        key=lambda e: (e.end_year or 0, e.institution or ""),
        reverse=True,
    )

    field_confidence = {
        group: round(sum(vals) / len(vals), 4) for group, vals in m.group_confs.items() if vals
    }
    provenance = sorted(
        (Provenance(field=f, source=s, method=mth) for (f, s, mth) in m.provenance),
        key=lambda p: (p.field, p.source, p.method),
    )

    profile = CandidateProfile(
        candidate_id=candidate_id,
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
        headline=headline,
        years_experience=years,
        skills=skills,
        experience=experience,
        education=education,
        provenance=provenance,
        field_confidence=field_confidence,
        overall_confidence=conf.overall_confidence(field_confidence),
    )
    return profile
