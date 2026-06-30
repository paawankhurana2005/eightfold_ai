# Multi-Source Candidate Data Transformer

Turns messy candidate data from many sources into **one clean, canonical profile per
candidate** — normalized formats, deduplicated across sources, with **provenance and
confidence on every value**. A runtime config can reshape the output with **no code
changes**. Guiding principle: *wrong-but-confident is worse than honestly-empty* — unknown
values become `null`, never invented.

Built for the Eightfold take-home. See [`design/DESIGN.md`](design/DESIGN.md) (and the
one-page PDF) for the Stage-1 design.

## What sets it apart

Most ingestion pipelines stop at "merge the fields." This one is built around the harder
questions — *how sure are we, where did each value come from, and what happens when a
source is garbage* — and makes the answers first-class:

- **Provenance + confidence on every value, not just a final blob.** Each field records
  which source won, how it was extracted, and a deterministic confidence score built from an
  explicit trust table, independent-source corroboration, and a fuzzy-match discount. There
  is no hand-wavy "AI score" — the math is auditable and reproducible (`confidence.py`).
- **Honestly-empty over wrong-but-confident.** A value that can't be normalized or verified
  becomes `null`; nothing is ever invented to fill a gap.
- **A hard projection wall.** The internal canonical record and the output shape are fully
  decoupled: a runtime JSON config renames/remaps fields, applies per-field normalization,
  toggles provenance/confidence, and is validated against a schema *derived from the config
  itself* — all with **zero code changes**.
- **Robust by construction.** Source adapters never throw; a malformed or empty source
  degrades to a warning and the profile is still built from whatever remains. One bad file
  can't take down a batch of thousands.
- **Deterministic end to end.** Stable sorts, hash-derived identities, and recorded fixtures
  mean the same inputs always produce byte-identical output — easy to diff, test, and trust.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Default canonical schema over all sample candidates -> stdout
python -m transformer transform --inputs samples/inputs --pretty

# Default schema, written to a file
python -m transformer transform --inputs samples/inputs \
    --config samples/configs/default.json --pretty --out out.json

# A custom config (rename/remap + per-field normalize + confidence), one candidate
python -m transformer transform --inputs samples/inputs/jane-mcdonald \
    --config samples/configs/custom_recruiter_summary.json --pretty
```

Warnings (missing/garbage sources, skipped files) go to **stderr**; clean JSON goes to
**stdout** (or `--out`). When inputs resolve to one candidate the output is a single
object; for several candidates it is a JSON array.

## CLI

```
python -m transformer transform --inputs <dir|files...> [--config cfg.json]
       [--out out.json | -] [--live] [--cache-dir DIR] [--pretty]
```

- `--inputs` — a directory of candidate sub-folders (one candidate each), a single
  candidate folder, or explicit files.
- `--config` — projection config JSON. Omit for the built-in default canonical schema.
- `--live` — allow real GitHub API calls. **Default is deterministic fixtures** (`github.json`).
- `--cache-dir` — where GitHub fixtures live / live responses are cached.

## How it works

```
ingest → extract (per-source adapters) → normalize → merge/dedupe
       → score confidence → canonical record → project (config) → validate → emit
```

- **Sources** (`src/transformer/sources/`): Recruiter CSV, ATS JSON (explicit foreign-key
  remap), GitHub (fixture/`--live`), Resume (PDF/DOCX/TXT), Recruiter notes. Adapters
  **never throw** — a bad source returns `[]` + a warning.
- **Normalize** (`src/transformer/normalize/`): phones→E.164, dates→`YYYY-MM`,
  country→ISO-3166 alpha-2, skills→canonical alias dictionary, emails lowercased. A value
  that won't normalize is dropped (never invented).
- **Merge** (`src/transformer/merge.py`): 3-tier `candidate_id` identity, trust-ranked
  scalar winners, unioned lists, provenance + confidence per field.
- **Confidence** (`src/transformer/confidence.py`): explicit trust table + corroboration +
  fuzzy discount; see the design doc for the formula.
- **Projection** (`src/transformer/projection/`): a path-DSL resolver, the projector
  (rename/remap, per-field normalize, `on_missing` policy, provenance/confidence toggles),
  and a validator that builds a JSON Schema from the config and checks the output.

## Configs & sample outputs

| Config | What it shows | Output |
|---|---|---|
| `samples/configs/default.json` | Full canonical schema | `samples/outputs/default.json` |
| `samples/configs/custom_recruiter_summary.json` | Rename/remap, `from` paths, E.164 + canonical normalize, confidence on, provenance off | `samples/outputs/custom_recruiter_summary.json` |
| `samples/configs/custom_min_pii.json` | Field subset, `on_missing: omit`, confidence/provenance off | `samples/outputs/custom_min_pii.json` |

Regenerate outputs:

```bash
python -m transformer transform --inputs samples/inputs --config samples/configs/default.json --pretty --out samples/outputs/default.json
python -m transformer transform --inputs samples/inputs/jane-mcdonald --config samples/configs/custom_recruiter_summary.json --pretty --out samples/outputs/custom_recruiter_summary.json
python -m transformer transform --inputs samples/inputs --config samples/configs/custom_min_pii.json --pretty --out samples/outputs/custom_min_pii.json
```

## Sample candidates (chosen to exercise the hard parts)

- **jane-mcdonald** — all 5 sources, a name-casing conflict (`Jane Mcdonald` from ATS vs
  `Jane McDonald` elsewhere) resolved by trust but still corroborated to 0.99; skills
  unioned across sources; deduped education.
- **liang-wei** — **no email anywhere** → identity falls back to name+phone; country
  `The Netherlands` is **fuzzy-matched** to `NL` and confidence-discounted.
- **marco-rossi** — **robustness**: a malformed `ats.json` and an empty `recruiter.csv` are
  skipped with warnings, and the profile is still produced from the DOCX resume + notes.

## Tests

```bash
pytest -q
```

Covers each normalizer, merge/conflict resolution, the confidence math, the ATS remap, the
3-tier identity chain, the resume scope boundary, the projection layer (incl. all three
`on_missing` schema paths), robustness (garbage/empty sources don't crash; unknowns stay
null), an end-to-end run, and a **gold-profile** comparison
(`tests/fixtures/gold_jane.json`).

## Determinism

Same inputs always produce the same output (stable sorts, derived ids, fixtures by
default). Verify:

```bash
python -m transformer transform --inputs samples/inputs --config samples/configs/default.json --pretty --out /tmp/a.json
python -m transformer transform --inputs samples/inputs --config samples/configs/default.json --pretty --out /tmp/b.json
diff /tmp/a.json /tmp/b.json   # identical
```

## Assumptions & scope

- **One candidate per input folder.** Cross-source dedupe happens within a folder; the
  3-tier identity chain is the mechanism that would cluster flat inputs by identity.
- **GitHub uses recorded fixtures by default** for determinism; `--live` hits the real API.
- **Binary sample resumes** (`resume.pdf`, `resume.docx`) are generated by
  `samples/make_sample_docs.py` so they're reproducible.
- **Intentional scope boundaries** (chosen to keep the system deterministic and explainable):
  LinkedIn scraping is excluded (no public API); resume parsing uses deterministic
  regex/section heuristics rather than ML/NLP, and those values are flagged low-confidence;
  cross-candidate identity is limited to the 3-tier chain (no fuzzy clustering); and the
  surface is a clean CLI rather than a UI.
