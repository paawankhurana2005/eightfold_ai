"""Presentation-only rendering of run warnings to stderr (demo-friendly, colored).

This module is purely cosmetic: it reformats the warning strings the pipeline already
produces into colored, leveled lines and a one-line batch summary. It changes NOTHING
about stdout (the JSON payload) and nothing about pipeline/merge/confidence behavior.

Severity model — most of what the pipeline reports is a HANDLED degradation, not a
failure, so it renders YELLOW (a skipped/empty/garbage source that the run recovered
from). Only a true crash (a candidate the pipeline could not produce output for) renders
RED. The end-of-run summary is GREEN.
"""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.text import Text

# Stages that mean "we produced no output for this candidate" -> a real failure (red).
_ERROR_STAGES = {"pipeline", "projection"}

# Phrases that mean a source contributed NOTHING and was dropped (vs. merely degraded,
# e.g. "ignored unmapped fields", where the source still contributed claims).
_HARD_SKIP_MARKERS = (
    "empty file",
    "invalid json",
    "no extractable text",
    "unsupported",
    "skipped unrecognized",
    "not an object",
    "no header",
    "no data rows",
    "bad fixture",
    "no cached",
    "no username",
    "no url",
    "live fetch failed",
    "failed to read",
)

_PATH_TOKEN = re.compile(r"\S*/(\S+)")


def _shorten_paths(text: str) -> str:
    """Collapse any path-like token to its basename for compact display."""
    return _PATH_TOKEN.sub(lambda m: m.group(1), text)


def _split_stage(warning: str) -> tuple[str, str]:
    stage, _, rest = warning.partition(": ")
    return stage, rest or stage


def _is_hard_skip(rest: str) -> bool:
    low = rest.lower()
    return any(marker in low for marker in _HARD_SKIP_MARKERS)


class WarningReporter:
    """Renders per-candidate warnings and a batch summary to a stderr Console."""

    def __init__(self, no_color: bool = False) -> None:
        # rich auto-disables ANSI when stderr is not a TTY (piping/CI). ``--no-color``
        # additionally forces fully plain text on a TTY by killing the color system
        # outright (no bold/dim either). highlight=False keeps our styling exact.
        self.console = Console(
            stderr=True,
            highlight=False,
            color_system=None if no_color else "auto",
        )
        self.sources_skipped = 0

    def report(self, name: str, files: list[Path], warnings: list[str], crashed: bool) -> None:
        """Render every warning for one candidate, then a 'built from' fallback line."""
        skipped_files: set[str] = set()
        for warning in warnings:
            stage, rest = _split_stage(warning)
            hard_skip = _is_hard_skip(rest)
            error = stage in _ERROR_STAGES
            if hard_skip:
                self.sources_skipped += 1

            source_file = next((f.name for f in files if f.name in warning), None)
            if source_file and hard_skip:
                skipped_files.add(source_file)

            self._line(name, source_file or stage, _shorten_paths(rest), error)

        if not crashed:
            self._fallback(files, skipped_files)

    def _line(self, name: str, source: str, reason: str, error: bool) -> None:
        color = "red" if error else "yellow"
        icon = "✗" if error else "⚠"
        line = Text()
        line.append(f"{icon} ", style=color)
        line.append(name, style="bold")
        line.append(" · ")
        line.append(source, style="cyan")
        line.append(" — ")
        line.append(reason, style=color)
        self.console.print(line, soft_wrap=True)

    def _fallback(self, files: list[Path], skipped_files: set[str]) -> None:
        if not skipped_files:
            return
        built = [f.name for f in files if f.name not in skipped_files]
        if not built:
            return
        line = Text("    → built from ", style="dim")
        line.append(", ".join(built), style="dim green")
        self.console.print(line, soft_wrap=True)

    def summary(self, processed: int, crashes: int) -> None:
        def plural(n: int, word: str) -> str:
            if n == 1:
                return f"{n} {word}"
            suffix = "es" if word.endswith(("s", "sh", "ch", "x")) else "s"
            return f"{n} {word}{suffix}"

        text = (
            f"✓ {plural(processed, 'candidate')} processed"
            f" · {plural(self.sources_skipped, 'source')} skipped"
            f" · {plural(crashes, 'crash')}"
        )
        style = "bold green" if crashes == 0 else "bold red"
        self.console.print(Text(text, style=style), soft_wrap=True)
