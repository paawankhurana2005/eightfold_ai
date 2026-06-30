"""Render the one-page Stage-1 design PDF from structured content (reportlab/platypus).

Run: ``python design/make_design_pdf.py``. Produces ``design/Eightfold_Design.pdf``.
Rename to ``<YourFullName>_<YourEmail>_Eightfold.pdf`` for submission (see README).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "Eightfold_Design.pdf"

styles = getSampleStyleSheet()
H_TITLE = ParagraphStyle("t", parent=styles["Title"], fontSize=13, leading=15, spaceAfter=2)
H_SUB = ParagraphStyle("sub", parent=styles["Normal"], fontSize=7.5, leading=9, textColor=colors.HexColor("#444444"), spaceAfter=4)
H = ParagraphStyle("h", parent=styles["Heading2"], fontSize=8.6, leading=10, spaceBefore=4, spaceAfter=1, textColor=colors.HexColor("#1a3e72"))
P = ParagraphStyle("p", parent=styles["Normal"], fontSize=7.4, leading=8.8, alignment=TA_LEFT, spaceAfter=1)
CODE = ParagraphStyle("c", parent=styles["Code"], fontSize=6.8, leading=8.2, backColor=colors.HexColor("#f3f3f3"), spaceAfter=2, spaceBefore=1)


def P_(text):
    return Paragraph(text, P)


def H_(text):
    return Paragraph(text, H)


def trust_table():
    data = [
        ["Source", "ATS", "CSV", "Resume", "GitHub", "Notes"],
        ["Base trust", "0.90", "0.85", "0.60", "0.50", "0.35"],
    ]
    t = Table(data, colWidths=[0.95 * inch] + [0.78 * inch] * 5)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3e72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#eef2f8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.45 * inch, bottomMargin=0.4 * inch,
    )
    story = []
    story.append(Paragraph("Multi-Source Candidate Data Transformer — Design (Stage 1)", H_TITLE))
    story.append(Paragraph(
        "Turn messy, conflicting, multi-source candidate inputs into <b>one canonical profile</b> "
        "with provenance and confidence on every value. Principle: <i>wrong-but-confident is worse "
        "than honestly-empty</i> — unknowns become <font face='Courier'>null</font>, never invented.",
        H_SUB))

    story.append(H_("Pipeline"))
    story.append(P_("<font face='Courier'>ingest → extract (per-source adapters) → normalize → "
                    "merge/dedupe → score confidence → canonical record → project (runtime config) → "
                    "validate → emit</font>"))
    story.append(P_("<b>extract</b>: each adapter emits raw claims <i>(path, value, source, method)</i> "
                    "and <b>never throws</b> — a bad source returns <font face='Courier'>[]</font> + a "
                    "warning. <b>normalize</b>: pure functions canonicalize; a value that won't normalize "
                    "is <b>dropped</b>. <b>merge</b>: claims → one CandidateProfile (single source of truth)."))

    story.append(H_("Canonical schema &amp; normalized formats"))
    story.append(P_("<b>Fields:</b> <font face='Courier'>candidate_id, full_name, emails[], phones[], "
                    "location{city,region,country}, links{linkedin,github,portfolio,other[]}, headline, "
                    "years_experience, skills[{name,confidence,sources[],verified_in_code}], "
                    "experience[{company,title,start,end,summary}], education[{institution,degree,field,"
                    "end_year}], provenance[{field,source,method}], overall_confidence</font>."))
    story.append(P_("Phones → E.164; dates → <font face='Courier'>YYYY-MM</font> (a bare year is dropped, "
                    "never invented as -01); country → ISO-3166 alpha-2 (exact or flagged-fuzzy); skills → "
                    "canonical via an alias dictionary (js→JavaScript), unknowns kept &amp; acronyms preserved; "
                    "emails lowercased/validated."))

    story.append(H_("Sources (≥1 structured + ≥1 unstructured)"))
    story.append(P_("Structured: <b>Recruiter CSV</b>, <b>ATS JSON</b> (foreign field names → an "
                    "<b>explicit remap dict</b>; unmapped keys logged, never guessed). Unstructured: "
                    "<b>GitHub</b> (recorded fixture by default, <font face='Courier'>--live</font> for the "
                    "real API), <b>Resume PDF/DOCX</b>, <b>Recruiter notes</b>."))

    story.append(H_("Merge &amp; conflict resolution"))
    story.append(P_("<b>Identity / candidate_id — 3 tiers:</b> (a) hash of best email; (b) name + matching "
                    "phone; (c) name + source-file identity. <b>Zero matchable identifiers → no cross-source "
                    "dedupe</b> (kept standalone). <b>Scalars:</b> highest source trust wins (tie-broken by "
                    "completeness, then stable order). <b>Lists</b> unioned &amp; de-duped. Corroboration is "
                    "case-insensitive. <b>Per skill <font face='Courier'>verified_in_code</font>:</b> each skill "
                    "is <font face='Courier'>{name, confidence, sources[], verified_in_code}</font>; the flag is "
                    "<font face='Courier'>true</font> iff <font face='Courier'>github</font> is among its sources "
                    "— a skill claimed in a resume but absent from the candidate's public code carries this flag "
                    "rather than being silently trusted as equally strong, and it does not alter confidence or "
                    "add a scoring path."))

    story.append(H_("Confidence (concrete math)"))
    story.append(trust_table())
    story.append(Paragraph(
        "per_field = base_trust(winner) + 0.05 * min(corroborations, 3)        # ≤ +0.15<br/>"
        "per_field *= 0.9   if value is fuzzy/regex-derived (resume regex, fuzzy country)<br/>"
        "per_field  = clamp(per_field, 0.05, 0.99)                            # never 1.0<br/>"
        "overall    = importance-weighted mean (identity fields weighted higher)", CODE))
    story.append(P_("<b>Worked examples (all reproducible from the shipped samples):</b> "
                    "Jane <font face='Courier'>full_name</font> = ATS \"Jane Mcdonald\" (0.90) + CSV+GitHub+resume "
                    "corroboration (+0.15) → clamp <b>0.99</b>; "
                    "Liang <font face='Courier'>location.country</font> \"The Netherlands\"→NL is fuzzy, from ATS "
                    "(0.90) + GitHub (+0.05 = 0.95) ×0.9 = <b>0.855</b>; "
                    "Jane <font face='Courier'>PostgreSQL</font> skill, resume-only via regex (fuzzy) → 0.60×0.9 = "
                    "<b>0.54</b>. <i>(Hypothetical, not in samples: a notes-only skill would floor at base "
                    "0.35.)</i>"))

    story.append(H_("Runtime config (projection + validation)"))
    story.append(P_("Config selects/renames fields (<font face='Courier'>from</font> DSL: "
                    "<font face='Courier'>emails[0]</font>, <font face='Courier'>skills[].name</font>), sets "
                    "per-field normalization, toggles provenance/confidence, and chooses a missing-value policy "
                    "driving <b>three schema shapes</b>: <b>omit</b> → not required; <b>null</b> → required + "
                    "nullable; <b>error</b> → required + non-null (missing fails loudly). Canonical record and "
                    "projection are strictly separated — default and any custom shape come from <b>one engine, "
                    "no code changes</b>."))

    story.append(H_("Edge cases handled"))
    story.append(P_("(1) Conflicting name casing → trust winner kept, others still corroborate. "
                    "(2) Malformed phone / bare-year date → dropped, stays null. "
                    "(3) Malformed JSON / empty CSV → skipped with a warning; other sources still produce a "
                    "profile. (4) Same skill, many spellings → canonicalized &amp; merged, sources combined. "
                    "(5) No email &amp; no phone match → kept standalone; dedupe not attempted."))

    story.append(H_("Scope boundaries (intentional)"))
    story.append(P_("Chosen deliberately to keep the system deterministic and explainable: LinkedIn scraping is "
                    "excluded (no public API); resume parsing uses deterministic regex/section heuristics rather "
                    "than ML/NLP, and those values are flagged low-confidence; cross-candidate identity is limited "
                    "to the 3-tier chain (no fuzzy clustering); and the surface is a clean CLI rather than a UI."))

    doc.build(story)


if __name__ == "__main__":
    build()
    print(f"wrote {OUT}")
