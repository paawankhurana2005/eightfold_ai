"""Thin CLI surface: point it at inputs + a config, get validated JSON out.

Usage:
    python -m transformer transform --inputs <dir|files...> [--config cfg.json]
        [--out out.json] [--live] [--pretty] [--cache-dir DIR]

Defaults to the full canonical schema if no --config is given. Writes to stdout unless
--out is set. Warnings (missing/garbage sources, skipped files) go to stderr so stdout
stays clean JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import default_config, load_config
from .pipeline import discover_candidates, run_pipeline
from .reporting import WarningReporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="candidate-transformer",
        description="Transform messy multi-source candidate inputs into clean canonical profiles.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("transform", help="Run the transform pipeline.")
    t.add_argument("--inputs", nargs="+", required=True,
                   help="A candidates directory, a single-candidate directory, or input files.")
    t.add_argument("--config", default=None,
                   help="Projection config JSON. Omit for the default canonical schema.")
    t.add_argument("--out", default="-",
                   help="Output file path, or '-' for stdout (default).")
    t.add_argument("--live", action="store_true",
                   help="Allow live GitHub API calls (default: deterministic fixtures).")
    t.add_argument("--cache-dir", default=None,
                   help="Directory of GitHub fixtures / live-fetch cache.")
    t.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output.")
    t.add_argument("--no-color", action="store_true",
                   help="Disable colored stderr warnings (auto-disabled when piped).")
    return parser


def _write(output_text: str, out: str) -> None:
    if out == "-":
        sys.stdout.write(output_text + "\n")
    else:
        Path(out).write_text(output_text + "\n", encoding="utf-8")


def cmd_transform(args: argparse.Namespace) -> int:
    config = load_config(args.config) if args.config else default_config()
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    inputs = [Path(p) for p in args.inputs]

    results = list(run_pipeline(inputs, config, live=args.live, cache_dir=cache_dir))

    files_by_key = dict(discover_candidates(inputs))
    reporter = WarningReporter(no_color=args.no_color)

    profiles = []
    exit_code = 0
    crashes = 0
    for r in results:
        crashed = r.output is None
        if r.warnings:
            name = r.profile.full_name or r.key
            reporter.report(name, files_by_key.get(r.key, []), r.warnings, crashed)
        if crashed:
            exit_code = 1
            crashes += 1
            continue
        profiles.append(r.output)
    if len(results) > 1:
        reporter.summary(processed=len(profiles), crashes=crashes)

    payload = profiles[0] if len(profiles) == 1 else profiles
    indent = 2 if args.pretty else None
    _write(json.dumps(payload, indent=indent, ensure_ascii=False, sort_keys=False), args.out)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "transform":
        return cmd_transform(args)
    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
