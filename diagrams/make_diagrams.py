"""Generate the 4 Excalidraw demo scenes (committed so they're reproducible).

Run: ``python diagrams/make_diagrams.py``  ->  writes diagrams/*.excalidraw
Each file is valid .excalidraw v2 JSON (File > Open / drag-drop at excalidraw.com).

Eightfold palette (consistent across all 4):
  purple  structural boxes/borders   orange  arrows / winners / flow / emphasis
  green   confident / validated / verified   amber  degraded / fuzzy (never red — all handled)
  gray    absent / missing
Roughness 1-2 + hachure fill for the authentic hand-sketched look.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- palette ---------------------------------------------------------------------- #
INK = "#1e1e1e"
PURPLE, PURPLE_BG = "#5b2c91", "#e7dbf6"
ORANGE, ORANGE_BG = "#ff6b35", "#ffd8c7"
GREEN, GREEN_BG = "#2f9e44", "#c3f0cb"
AMBER, AMBER_BG = "#e8920c", "#ffec99"
GRAY, GRAY_BG = "#868e96", "#e9ecef"

_seq = 0


def _ids() -> str:
    global _seq
    _seq += 1
    return f"el{_seq:04d}"


def _seed() -> int:
    return 100000 + _seq


def _base(t, x, y, w, h, **kw):
    el = {
        "id": _ids(), "type": t, "x": round(x), "y": round(y),
        "width": round(w), "height": round(h), "angle": 0,
        "strokeColor": INK, "backgroundColor": "transparent", "fillStyle": "hachure",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None, "seed": _seed(),
        "version": 1, "versionNonce": _seed() + 5, "isDeleted": False,
        "boundElements": [], "updated": 1717000000000, "link": None, "locked": False,
    }
    el.update(kw)
    return el


def _tw(s, size):
    longest = max((len(ln) for ln in s.split("\n")), default=1)
    return max(longest * size * 0.58, size)


def _th(s, size):
    return (s.count("\n") + 1) * size * 1.25


class Scene:
    def __init__(self):
        self.elements = []

    def rect(self, x, y, w, h, stroke=PURPLE, bg="transparent", sw=2, style="solid",
             rough=1, rounded=True):
        el = _base("rectangle", x, y, w, h, strokeColor=stroke, backgroundColor=bg,
                   strokeWidth=sw, strokeStyle=style, roughness=rough,
                   roundness={"type": 3} if rounded else None)
        self.elements.append(el)
        return el

    def ellipse(self, x, y, w, h, stroke=PURPLE, bg="transparent", sw=2, rough=1):
        el = _base("ellipse", x, y, w, h, strokeColor=stroke, backgroundColor=bg,
                   strokeWidth=sw, roughness=rough)
        self.elements.append(el)
        return el

    def diamond(self, x, y, w, h, stroke=PURPLE, bg="transparent", sw=2, rough=1):
        el = _base("diamond", x, y, w, h, strokeColor=stroke, backgroundColor=bg,
                   strokeWidth=sw, roughness=rough)
        self.elements.append(el)
        return el

    def text(self, x, y, s, size=16, color=INK, align="left", family=1):
        el = _base("text", x, y, _tw(s, size), _th(s, size), strokeColor=color,
                   roughness=1, roundness=None, text=s, fontSize=size, fontFamily=family,
                   textAlign=align, verticalAlign="top", baseline=round(size * 0.9),
                   containerId=None, originalText=s, lineHeight=1.25, autoResize=True)
        self.elements.append(el)
        return el

    def center(self, cx, cy, s, size=16, color=INK, family=1):
        """Single/multi-line text centered on (cx, cy)."""
        return self.text(cx - _tw(s, size) / 2, cy - _th(s, size) / 2, s, size, color,
                         "center", family)

    def label_box(self, x, y, w, h, s, size=16, stroke=PURPLE, bg="transparent",
                  txt=INK, sw=2, style="solid", rough=1):
        self.rect(x, y, w, h, stroke, bg, sw, style, rough)
        self.center(x + w / 2, y + h / 2, s, size, txt)

    def arrow(self, x1, y1, x2, y2, color=ORANGE, sw=2.5, dashed=False, pts=None):
        if pts is None:
            pts = [[0, 0], [x2 - x1, y2 - y1]]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        el = _base("arrow", x1, y1, max(abs(max(xs) - min(xs)), 1),
                   max(abs(max(ys) - min(ys)), 1), strokeColor=color, strokeWidth=sw,
                   strokeStyle="dashed" if dashed else "solid",
                   roundness={"type": 2}, points=pts, lastCommittedPoint=None,
                   startBinding=None, endBinding=None, startArrowhead=None,
                   endArrowhead="arrow")
        self.elements.append(el)
        return el

    def line(self, x1, y1, x2, y2, color=INK, sw=2, dashed=False):
        el = _base("line", x1, y1, abs(x2 - x1), abs(y2 - y1), strokeColor=color,
                   strokeWidth=sw, strokeStyle="dashed" if dashed else "solid",
                   roundness=None, points=[[0, 0], [x2 - x1, y2 - y1]],
                   lastCommittedPoint=None, startBinding=None, endBinding=None,
                   startArrowhead=None, endArrowhead=None)
        self.elements.append(el)
        return el

    def chip(self, x, y, s, size=11, stroke=GREEN, txt=GREEN):
        w = _tw(s, size) + 22
        h = size * 2.1
        self.rect(x, y, w, h, stroke, "transparent", 1.5, rough=2)
        self.center(x + w / 2, y + h / 2, s, size, txt)
        return w

    def footer(self, x, y, items, stroke=GREEN, txt=GREEN, title="our moat:"):
        self.text(x, y - 22, title, 13, GRAY, family=2)
        cx = x
        for it in items:
            cx += self.chip(cx, y, it, 11, stroke, txt) + 12

    def dump(self, name):
        doc = {
            "type": "excalidraw", "version": 2,
            "source": "https://excalidraw.com",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        out = HERE / name
        out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return out


# ============================================================================ #
# 1. architecture.excalidraw — 8-stage pipeline, opening orientation
# ============================================================================ #
def architecture():
    s = Scene()
    s.text(40, 22, "Pipeline architecture — messy multi-source in, one canonical profile out",
           26, PURPLE)
    s.text(40, 58, "ingest → extract → normalize → merge → confidence → canonical record → project → validate → emit",
           13, GRAY, family=3)

    stages = [
        ("ingest", "source-type detection\nvia filename heuristic", PURPLE),
        ("extract", "fault-isolated adapters:\ndegrade to empty result-set\n+ warning; never propagate\nexceptions", PURPLE),
        ("normalize", "pure normalization\nfunctions: failed parse →\nclaim discarded — no\nvalue fabrication", PURPLE),
        ("merge", "deterministic identity\nresolution (3-tier fallback)\n+ trust-ranked conflict\nresolution", PURPLE),
        ("confidence", "per-field confidence\nscoring: source trust ×\ncorroboration ×\nextraction-method reliability", ORANGE),
        ("canonical\nrecord", "single canonical\nrepresentation\n(pydantic-validated),\ndecoupled from output shape", PURPLE),
        ("project", "config-driven projection\nlayer — schema reshaping\nwithout pipeline\nmodification", PURPLE),
        ("validate", "runtime JSON Schema\nsynthesis + validation,\npre-emit", GREEN),
        ("emit", "deterministic\nserialization;\nstdout/stderr stream\nseparation", PURPLE),
    ]
    bx, by, bw, bh, pitch = 40, 250, 150, 78, 188
    centers = []
    for i, (label, ann, col) in enumerate(stages):
        x = bx + i * pitch
        bg = ORANGE_BG if col == ORANGE else (GREEN_BG if col == GREEN else PURPLE_BG)
        s.label_box(x, by, bw, bh, label, 17, col, bg, INK, sw=2)
        s.center(x + bw / 2, by + bh + 26, ann, 11, GRAY)
        centers.append((x, x + bw / 2))
        if i:
            px = bx + (i - 1) * pitch + bw
            s.arrow(px + 4, by + bh / 2, x - 4, by + bh / 2, ORANGE, 2.5)

    # claim token floating above the extract -> normalize boundary
    tx, ty = 360, 150
    s.rect(tx, ty, 250, 56, ORANGE, ORANGE_BG, 2, rough=2)
    s.center(tx + 125, ty + 20, "Claim — immutable IR", 13, ORANGE)
    s.center(tx + 125, ty + 38, "{path, value, source, method}", 10, INK)
    s.arrow(tx + 125, ty + 56, 414 + 75, by - 4, ORANGE, 2, pts=[[0, 0], [0, 40], [414 + 75 - tx - 125, by - 4 - ty - 56]])
    s.text(tx + 258, ty + 16, "raw claims\nflow downstream", 10, GRAY)

    # 5 source adapters in a column below the extract stage, with trust scores.
    # Intro label + column sit well below the extract caption (which ends at y~368).
    ex = bx + 1 * pitch
    s.text(ex - 48, 388, "extract = 5 source adapters (trust score on each):", 12, PURPLE)
    adapters = [
        ("recruiter_csv", "0.85", "structured", PURPLE),
        ("ats_json", "0.90", "structured", PURPLE),
        ("github", "0.50", "unstructured", PURPLE),
        ("resume", "0.60", "unstructured", PURPLE),
        ("recruiter_notes", "0.35", "unstructured", AMBER),
    ]
    ax, ay, aw, ah, ap = ex - 30, 412, 220, 44, 50
    for i, (nm, tr, kind, col) in enumerate(adapters):
        y = ay + i * ap
        s.rect(ax, y, aw, ah, col, PURPLE_BG, 1.8, rough=2)
        s.text(ax + 12, y + 13, nm, 13, INK)
        s.center(ax + aw - 30, y + ah / 2, tr, 15, ORANGE)
        s.text(ax + 12, y + 28, kind, 9, GRAY)
    # single clean curve from the extract box's bottom-left down into the column,
    # bowing left of the caption so it never crosses any text.
    s.arrow(ex, by + bh + 2, ex - 28, 384, ORANGE, 2.5,
            pts=[[0, 0], [-22, 28], [-28, 54]])

    # palette legend (this is the orientation slide)
    lx, ly = 1090, 400
    s.rect(lx, ly, 300, 168, GRAY, "transparent", 1.5, rounded=True)
    s.text(lx + 14, ly + 10, "legend", 14, GRAY, family=2)
    legend = [
        ("purple = structure / pipeline stage", PURPLE),
        ("orange = winner / flow / emphasis", ORANGE),
        ("green = verified / validated", GREEN),
        ("amber = degraded / fuzzy (handled)", AMBER),
        ("gray = absent / missing", GRAY),
    ]
    for i, (txt, col) in enumerate(legend):
        yy = ly + 40 + i * 25
        s.rect(lx + 16, yy, 18, 14, col, col, 1.5, rough=2)
        s.text(lx + 44, yy, txt, 11, INK)

    s.footer(40, 700, ["provenance + confidence on EVERY value", "deterministic: same bytes",
                       "garbage source never crashes the run", "config-driven output",
                       "fully explainable"], GREEN, GREEN)
    return s.dump("architecture.excalidraw")


# ============================================================================ #
# 2. merge_confidence_sequence.excalidraw — Liang location.country, two stacked steps
# ============================================================================ #
def merge_confidence():
    s = Scene()
    s.text(40, 22, "Merge + confidence — corroboration and uncertainty, stacked", 25, PURPLE)
    s.text(40, 56, "Liang's location.country: agreement raises confidence, then fuzzy matching discounts it",
           13, GRAY, family=2)

    # --- 2 source boxes (only two sources have this field) ---
    sx, sw = 40, 210
    s.rect(sx, 150, sw, 88, ORANGE, ORANGE_BG, 2.4)
    s.text(sx + 14, 162, "ats_json   ★ WINNER", 14, ORANGE)
    s.text(sx + 14, 186, '"The Netherlands"', 13, INK)
    s.text(sx + 14, 210, "trust 0.90", 12, GRAY)
    s.rect(sx, 252, sw, 88, PURPLE, PURPLE_BG, 1.8)
    s.text(sx + 14, 264, "github", 14, INK)
    s.text(sx + 14, 288, '"The Netherlands"', 13, INK)
    s.text(sx + 14, 312, "trust 0.50", 12, GRAY)
    s.center(sx + sw - 22, 296, "✓", 20, GREEN)
    s.text(sx, 348, "✓ corroborates (case-insensitive)", 11, GREEN)

    # --- STEP 1: corroboration boost -> 0.95 subtotal (orange) ---
    s.rect(290, 160, 200, 180, ORANGE, "#fff6f1", 2.2)
    s.center(390, 180, "STEP 1 — corroboration", 13, ORANGE)
    s.text(306, 200, "trust ranking", 11, GRAY)
    s.text(312, 220, "ats 0.90  ← winner", 13, ORANGE)
    s.text(312, 242, "github 0.50 → corrob.", 12, INK)
    s.line(306, 272, 474, 272, ORANGE, 1.2)
    s.center(390, 290, "0.90 + 0.05 (corrob)", 13, INK)
    s.center(390, 314, "= 0.95 subtotal", 16, ORANGE)

    # --- STEP 2: fuzzy normalize -> x0.9 discount -> 0.855 (amber) ---
    s.rect(528, 160, 235, 180, AMBER, "#fffdf0", 2.2)
    s.center(645, 180, "STEP 2 — fuzzy normalize", 13, AMBER)
    s.text(544, 200, '"The Netherlands"', 12, INK, family=3)
    s.text(544, 222, "→ pycountry fuzzy match", 11, AMBER)
    s.text(544, 244, '→ "NL"  (ISO-3166)', 13, GREEN, family=3)
    s.line(544, 272, 747, 272, AMBER, 1.2)
    s.center(645, 290, "0.95 × 0.9 (fuzzy)", 13, INK)
    s.center(645, 314, "= 0.855", 16, AMBER)
    s.text(528, 348, "× 0.9 — fuzzy penalty on the subtotal", 11, AMBER)

    # --- arrows: sources -> STEP 1 -> STEP 2 (carrying the intermediate numbers) ---
    s.arrow(sx + sw + 4, 194, 286, 248, ORANGE, 2)        # ats -> step1
    s.arrow(sx + sw + 4, 296, 286, 252, ORANGE, 2)        # github -> step1
    s.arrow(494, 250, 524, 250, ORANGE, 2.6)              # step1 -> step2
    s.text(497, 226, "0.95", 12, ORANGE)
    s.arrow(767, 250, 796, 256, AMBER, 2.6)               # step2 -> result
    s.text(764, 226, "0.855", 12, AMBER)

    # --- final result (validated, green) ---
    s.rect(800, 185, 265, 150, GREEN, GREEN_BG, 2.6)
    s.center(932, 206, "✓ CANONICAL RESULT", 15, GREEN)
    s.line(816, 228, 1049, 228, GREEN, 1.5)
    s.text(822, 240, "location.country:", 12, GRAY)
    s.text(822, 260, '"NL"', 18, INK)
    s.text(822, 292, "confidence  0.855", 16, GREEN)
    s.text(822, 316, "ISO-3166 · 2 sources", 10, GRAY)
    s.text(800, 346, "▲ not higher: fuzzy match, discounted × 0.9", 11, AMBER)
    s.text(800, 368, "▲ not lower: still corroborated by 2 sources", 11, GREEN)

    s.text(40, 392, "takeaway: confidence reflects BOTH how much sources agree AND how the value was derived.",
           11, PURPLE)

    # --- secondary inset (demoted Jane example, low visual weight) ---
    s.rect(40, 424, 720, 88, GRAY, "transparent", 1.6)
    s.text(54, 436, "side note — full agreement still isn't certainty", 12, GRAY)
    s.text(54, 462, "Jane's full_name: 4 sources agree → 0.90 + 0.15 = 1.05 → clamped to 0.99, never 1.0.",
           12, INK)

    s.footer(40, 580, ["two mechanisms stack", "fuzzy flagged & discounted (×0.9)",
                       "agreement raises, never invents", "calibrated: clamp < 1.0"], GREEN, GREEN)
    return s.dump("merge_confidence_sequence.excalidraw")


# ============================================================================ #
# 3. canonical_projection_wall.excalidraw — the projection wall
# ============================================================================ #
def projection_wall():
    s = Scene()
    s.text(40, 22, "The projection wall — one record, any output shape, zero code changes", 25, PURPLE)

    # canonical record (left)
    cx, cy, cw, ch = 50, 110, 360, 430
    s.rect(cx, cy, cw, ch, PURPLE, PURPLE_BG, 2.6)
    s.center(cx + cw / 2, cy + 26, "CandidateProfile", 19, PURPLE)
    s.center(cx + cw / 2, cy + 48, "(canonical record — single source of truth)", 11, GRAY)
    s.line(cx + 18, cy + 66, cx + cw - 18, cy + 66, PURPLE, 1.5)
    fields = [
        "candidate_id: cand_996067f363f2",
        'full_name:    "Jane Mcdonald"',
        "emails[]:     jane.mcdonald@example.com",
        "phones[]:     +14155552671",
        "location:     {San Francisco, CA, US}",
        "links:        {github, linkedin, …}",
        "headline:     Staff Software Engineer",
        "years_experience: 9",
        "skills[]:     Python 0.99 ✓code, …",
        "experience[]: {Acme, 2021-03 → now}",
        "education[]:  {MIT, BS, 2014}",
        "+ provenance + overall_confidence",
    ]
    for i, f in enumerate(fields):
        s.text(cx + 22, cy + 80 + i * 28, f, 12, GREEN if "✓code" in f else INK, family=3)

    # the wall
    wx = 470
    s.line(wx, 96, wx, 560, AMBER, 5, dashed=True)
    s.center(wx, 80, "▲ THE WALL — no code changes, config only ▼", 13, AMBER)
    s.text(wx - 150, 568, "canonical record and output are strictly separated", 11, GRAY)

    # projector
    px, py, pw, ph = 530, 270, 170, 116
    s.rect(px, py, pw, ph, ORANGE, ORANGE_BG, 2.4)
    s.center(px + pw / 2, py + 26, "Projector", 17, ORANGE)
    s.line(px + 14, py + 44, px + pw - 14, py + 44, ORANGE, 1.5)
    s.center(px + pw / 2, py + 60, "path DSL: emails[0]\nskills[].name", 11, INK)
    s.center(px + pw / 2, py + 96, "+ per-field normalize", 10, GRAY)
    s.arrow(cx + cw + 4, cy + ch / 2, px - 4, py + ph / 2, ORANGE, 2.6)

    # default output (top right)
    dx, dy, dw, dh = 760, 110, 380, 200
    s.rect(dx, dy, dw, dh, GREEN, GREEN_BG, 2.4)
    s.center(dx + dw / 2, dy + 22, "default schema  (validated ✓)", 15, GREEN)
    s.line(dx + 16, dy + 42, dx + dw - 16, dy + 42, GREEN, 1.5)
    for i, f in enumerate([
        "candidate_id, full_name, emails[], phones[],",
        "location{}, links{}, headline, years_experience,",
        "skills[{name,confidence,sources[],verified_in_code}],",
        "experience[{}], education[{}],",
        "provenance[{}], overall_confidence",
    ]):
        s.text(dx + 22, dy + 54 + i * 26, f, 11, INK, family=3)
    s.arrow(px + pw + 4, py + 30, dx - 4, dy + dh / 2, ORANGE, 2.4,
            pts=[[0, 0], [40, 0], [dx - 4 - px - pw - 4 - 40, dy + dh / 2 - py - 30]])

    # custom recruiter output (bottom right)
    ux, uy, uw, uh = 760, 350, 380, 210
    s.rect(ux, uy, uw, uh, PURPLE, PURPLE_BG, 2.4)
    s.center(ux + uw / 2, uy + 22, "custom_recruiter_summary  (validated ✓)", 14, PURPLE)
    s.line(ux + 16, uy + 42, ux + uw - 16, uy + 42, PURPLE, 1.5)
    for i, f in enumerate([
        "primary_email  ← emails[0]",
        "phone          ← phones[0]   (E.164)",
        "name           ← full_name",
        "top_skills     ← skills[].name",
        "headline       ← headline",
    ]):
        s.text(ux + 22, uy + 54 + i * 26, f, 12, INK, family=3)
    s.text(ux + 22, uy + 186, "renamed + remapped · provenance off · confidence on", 10, ORANGE)
    s.arrow(px + pw + 4, py + ph - 30, ux - 4, uy + uh / 2, ORANGE, 2.4,
            pts=[[0, 0], [40, 0], [ux - 4 - px - pw - 4 - 40, uy + uh / 2 - py - ph + 30]])

    s.text(px - 10, py - 40, "same engine builds the\ndefault AND every custom shape", 11, GRAY)
    s.footer(40, 640, ["one engine, many schemas", "zero-code reshaping (config only)",
                       "validated before emit", "rename / remap / E.164 on the way out"],
             PURPLE, PURPLE)
    return s.dump("canonical_projection_wall.excalidraw")


# ============================================================================ #
# 4. identity_edge_case.excalidraw — Liang: we don't guess
# ============================================================================ #
def identity_edge_case():
    s = Scene()
    s.text(40, 22, "Edge case — Liang Wei: no email anywhere, fuzzy country. We don't guess.",
           24, PURPLE)

    # available sources box
    bx, by, bw, bh = 50, 110, 320, 250
    s.rect(bx, by, bw, bh, PURPLE, PURPLE_BG, 2.4)
    s.center(bx + bw / 2, by + 24, "available sources", 16, PURPLE)
    s.line(bx + 16, by + 44, bx + bw - 16, by + 44, PURPLE, 1.5)
    rows = [
        ("ats_json", "0.90", True), ("github", "0.50", True),
        ("recruiter_notes", "0.35", True),
    ]
    for i, (nm, tr, ok) in enumerate(rows):
        yy = by + 58 + i * 38
        s.center(bx + 28, yy + 8, "✓", 18, GREEN)
        s.text(bx + 48, yy, nm, 14, INK)
        s.center(bx + bw - 40, yy + 8, tr, 14, ORANGE)
    # absent csv (gray, crossed out)
    yy = by + 58 + 3 * 38
    s.rect(bx + 20, yy - 6, bw - 40, 34, GRAY, GRAY_BG, 1.5, style="dashed", rough=2)
    s.text(bx + 32, yy, "recruiter_csv : absent", 13, GRAY)
    s.line(bx + 28, yy + 10, bx + bw - 30, yy + 10, GRAY, 2)  # strike-through
    s.text(bx + 16, by + bh + 8, "⚠ no email present in ANY source", 12, AMBER)

    # 3-tier identity ladder
    lx, lw, lh, gap = 470, 320, 70, 30
    ladder = [
        ("Tier 1", "best email?  →  NO email", AMBER, AMBER_BG, "no identifier here"),
        ("Tier 2", "name + matching phone?  →  YES ✓", GREEN, GREEN_BG, "USED — deterministic match"),
        ("Tier 3", "name + source-file  (fallback)", GRAY, GRAY_BG, "not needed this time"),
    ]
    ly0 = 110
    for i, (tier, q, col, bg, note) in enumerate(ladder):
        y = ly0 + i * (lh + gap)
        s.rect(lx, y, lw, lh, col, bg, 2.4 if col == GREEN else 1.8)
        s.text(lx + 16, y + 12, tier, 14, col)
        s.text(lx + 16, y + 36, q, 13, INK)
        s.text(lx + lw + 14, y + 24, note, 11, col)
        if i:
            s.arrow(lx + lw / 2, y - gap + 2, lx + lw / 2, y - 4, ORANGE, 2.4)
    # candidate_id result
    cy = ly0 + 3 * (lh + gap)
    s.rect(lx, cy, lw, lh, PURPLE, PURPLE_BG, 2.6)
    s.center(lx + lw / 2, cy + 22, "candidate_id derived", 15, PURPLE)
    s.center(lx + lw / 2, cy + 46, "cand_ + sha1(name | phone)[:12]", 13, INK)
    s.arrow(lx + lw / 2, cy - gap + 2, lx + lw / 2, cy - 4, ORANGE, 2.4)
    s.arrow(bx + bw + 4, by + bh / 2, lx - 4, ly0 + lh / 2, ORANGE, 2.4,
            pts=[[0, 0], [lx - 4 - bx - bw - 4, ly0 + lh / 2 - by - bh / 2]])

    # fuzzy country side panel (shifted right so the Tier-3 caption never touches it)
    fx, fy, fw, fh = 940, 300, 340, 250
    s.rect(fx, fy, fw, fh, AMBER, "#fffdf0", 2.2)
    s.center(fx + fw / 2, fy + 22, "fuzzy country — flagged, not trusted blindly", 12, AMBER)
    s.line(fx + 16, fy + 42, fx + fw - 16, fy + 42, AMBER, 1.5)
    s.text(fx + 20, fy + 56, 'location.country: "The Netherlands"', 12, INK, family=3)
    s.arrow(fx + 60, fy + 84, fx + 60, fy + 104, AMBER, 2)
    s.text(fx + 78, fy + 86, "pycountry fuzzy match", 11, AMBER)
    s.text(fx + 20, fy + 110, 'normalized →  "NL"  (ISO-3166)', 13, GREEN, family=3)
    s.line(fx + 16, fy + 138, fx + fw - 16, fy + 138, AMBER, 1)
    s.text(fx + 20, fy + 148, "ATS 0.90 + GitHub corrob 0.05 = 0.95", 12, INK)
    s.center(fx + fw / 2, fy + 178, "× 0.9  (fuzzy penalty)", 15, AMBER)
    s.text(fx + 20, fy + 200, "confidence  =  0.855", 16, GREEN)
    s.text(fx + 20, fy + 224, "honest discount: we say so when we guessed", 10, GRAY)

    s.footer(40, 640, ["honest nulls over fake values", "fuzzy flagged & discounted (×0.9)",
                       "3-tier deterministic identity", "no email ≠ crash — handled"],
             GREEN, GREEN)
    return s.dump("identity_edge_case.excalidraw")


def main():
    outs = [architecture(), merge_confidence(), projection_wall(), identity_edge_case()]
    for o in outs:
        print("wrote", o)


if __name__ == "__main__":
    main()
