"""End-to-end orchestrator: ingest -> extract -> normalize -> merge -> project -> validate.

Candidates are processed one at a time via a generator so memory stays flat across
thousands of candidates. A single bad candidate (or source) is captured as a warning and
skipped — it never aborts the batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from .config import ProjectionConfig
from .merge import merge
from .models import CandidateProfile
from .normalize_stage import normalize_claims
from .projection import project
from .sources import (
    AtsJsonAdapter,
    GithubAdapter,
    RecruiterCsvAdapter,
    RecruiterNotesAdapter,
    ResumeAdapter,
    detect_source,
)


@dataclass
class CandidateResult:
    candidate_id: str
    key: str
    profile: CandidateProfile
    output: Optional[dict]
    warnings: list[str] = field(default_factory=list)


def _adapter_for(source: str, live: bool, cache_dir: Optional[Path]):
    if source == "recruiter_csv":
        return RecruiterCsvAdapter()
    if source == "ats_json":
        return AtsJsonAdapter()
    if source == "github":
        return GithubAdapter(live=live, cache_dir=cache_dir)
    if source == "resume":
        return ResumeAdapter()
    if source == "recruiter_notes":
        return RecruiterNotesAdapter()
    return None


def discover_candidates(inputs: list[Path]) -> list[tuple[str, list[Path]]]:
    """Group input paths into (candidate_key, files).

    * A single directory with subdirectories -> one candidate per subdirectory.
    * A single directory of files -> one candidate (the directory).
    * Explicit files -> one candidate.
    """
    paths = [Path(p) for p in inputs]
    if len(paths) == 1 and paths[0].is_dir():
        root = paths[0]
        entries = sorted(root.iterdir())
        subdirs = [e for e in entries if e.is_dir()]
        if subdirs:
            return [
                (sd.name, sorted(f for f in sd.iterdir() if f.is_file()))
                for sd in subdirs
            ]
        return [(root.name, [e for e in entries if e.is_file()])]
    files = [p for p in paths if p.is_file()]
    return [("candidate", sorted(files))]


def process_candidate(
    key: str, files: list[Path], live: bool, cache_dir: Optional[Path]
) -> tuple[CandidateProfile, list[str]]:
    claims = []
    warnings: list[str] = []
    for f in files:
        source = detect_source(f.name)
        if not source:
            warnings.append(f"ingest: skipped unrecognized file {f.name}")
            continue
        adapter = _adapter_for(source, live, cache_dir)
        result = adapter.safe_extract(f)
        claims.extend(result.claims)
        warnings.extend(result.warnings)
    normalized = normalize_claims(claims)
    profile = merge(normalized, identity_hint=key)
    return profile, warnings


def run_pipeline(
    inputs: list[Path],
    config: ProjectionConfig,
    live: bool = False,
    cache_dir: Optional[Path] = None,
) -> Iterator[CandidateResult]:
    for key, files in discover_candidates(inputs):
        warnings: list[str] = []
        try:
            profile, warnings = process_candidate(key, files, live, cache_dir)
        except Exception as exc:  # noqa: BLE001 - one bad candidate must not kill the batch
            yield CandidateResult(
                candidate_id="",
                key=key,
                profile=CandidateProfile(candidate_id=""),
                output=None,
                warnings=[f"pipeline: failed to process {key} ({exc.__class__.__name__}: {exc})"],
            )
            continue
        try:
            output = project(profile, config, validate=True)
        except Exception as exc:  # noqa: BLE001 - surface projection/validation failure, keep going
            yield CandidateResult(
                candidate_id=profile.candidate_id,
                key=key,
                profile=profile,
                output=None,
                warnings=warnings + [f"projection: {exc.__class__.__name__}: {exc}"],
            )
            continue
        yield CandidateResult(
            candidate_id=profile.candidate_id,
            key=key,
            profile=profile,
            output=output,
            warnings=warnings,
        )
