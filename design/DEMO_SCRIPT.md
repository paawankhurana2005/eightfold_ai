# Demo video script (~2 minutes)

A tight run-through. Have a terminal open at the repo root with the venv activated.

## 0:00–0:20 — What it is
> "This is a multi-source candidate transformer. It takes messy inputs — a recruiter CSV,
> an ATS JSON blob, a GitHub profile, a resume, recruiter notes — and produces one clean
> canonical profile per candidate, with provenance and confidence on every field. The core
> rule is: wrong-but-confident is worse than honestly-empty, so unknowns stay null."

Show `samples/inputs/` — three candidate folders.

## 0:20–0:50 — Default run
```bash
python -m transformer transform --inputs samples/inputs --pretty
```
> "One command over all three candidates. Notice the warnings on stderr — Marco's ATS JSON
> is malformed and his CSV is empty — but the run doesn't crash, and his profile is still
> built from the resume and notes. That's the robustness requirement."

Scroll to **Jane**: point at `skills` → `Python` with `confidence 0.99` and four sources.
> "Python shows up in four sources, so it's corroborated to 0.99. Provenance lists exactly
> where every value came from."

## 0:50–1:25 — Custom config (same engine, no code changes)
```bash
python -m transformer transform --inputs samples/inputs/jane-mcdonald \
    --config samples/configs/custom_recruiter_summary.json --pretty
```
> "Same engine, a different runtime config. It renames fields via `from` paths —
> `primary_email` from `emails[0]`, `phone` from `phones[0]` normalized to E.164, `skills`
> flattened from `skills[].name` — turns provenance off and keeps confidence. The output is
> validated against a schema generated from this config before it's returned."

(Optional) show `custom_min_pii.json` for a field subset with `on_missing: omit`.

## 1:25–1:50 — One design decision + one edge case
> "A decision I'm proud of: the strict wall between the internal canonical record and the
> projection layer. The default output and every custom shape go through the exact same
> code path — projection plus schema validation — so 'configurable output' is data, not new
> code."

> "An edge case: Liang has no email in any source. Identity falls back from email to
> name-plus-phone, and his country 'The Netherlands' is fuzzy-matched to NL, so its
> confidence is discounted. We never invent a value to look more complete."

## 1:50–2:00 — Tests
```bash
pytest -q
```
> "Tests cover the normalizers, the confidence math, the ATS remap, the identity chain, all
> three missing-value schema paths, robustness, and a gold-profile comparison. Deterministic:
> same inputs, same output, every time."
