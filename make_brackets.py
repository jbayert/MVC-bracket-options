"""
Generate bracket diagram SVGs for the three tournament formats.
Pure Python, no dependencies. Writes to site/brackets/*.svg.

Each format is an explicit list of game boxes placed on a (col, lane) grid.
A game box has a top slot and a bottom slot. A slot is either a seed label
(shown as text) or fed by a previous game (left blank, with a connector line
drawn in). This matches a standard tournament bracket look: fixed-size boxes
joined by elbow connectors.
"""
import os

# Geometry
BOXW = 150
ROWU = 24            # height of one slot
BOXH = 2 * ROWU      # a game box = two slots
COLW = BOXW + 66     # horizontal pitch between columns
LANE = 80            # vertical pitch between lanes
MARGIN_X = 24
MARGIN_TOP = 54

# Colors
BORDER = "#cbd5e1"
FILL = "#ffffff"
TEXT = "#1e293b"
SEEDTAG = "#2563eb"
LINE = "#94a3b8"
TITLE = "#0f172a"
BG = "#f8fafc"

def _x(col):
    return MARGIN_X + col * COLW

def _cy(lane):
    return MARGIN_TOP + lane * LANE

def _slot_text(x, y, label, is_seed):
    color = SEEDTAG if is_seed else TEXT
    weight = "700" if is_seed else "400"
    return (f'<text x="{x + 12:.1f}" y="{y + 5:.1f}" font-family="system-ui,Arial" '
            f'font-size="12" font-weight="{weight}" fill="{color}">{label}</text>')

def _game_svg(g):
    """Render one 2-slot game box."""
    x = _x(g["col"])
    cy = _cy(g["lane"])
    top = cy - ROWU
    parts = [
        f'<rect x="{x:.1f}" y="{top:.1f}" width="{BOXW}" height="{BOXH}" rx="5" '
        f'fill="{FILL}" stroke="{BORDER}" stroke-width="1.5"/>',
        f'<line x1="{x:.1f}" y1="{cy:.1f}" x2="{x+BOXW:.1f}" y2="{cy:.1f}" '
        f'stroke="{BORDER}" stroke-width="1"/>',
    ]
    if g.get("top"):
        parts.append(_slot_text(x, cy - ROWU/2, g["top"], g.get("top_seed", True)))
    if g.get("bottom"):
        parts.append(_slot_text(x, cy + ROWU/2, g["bottom"], g.get("bottom_seed", True)))
    return "\n".join(parts)

def _single_svg(g):
    """Render a single-slot box (the champion)."""
    x = _x(g["col"])
    cy = _cy(g["lane"])
    h = 34
    top = cy - h/2
    return (
        f'<rect x="{x:.1f}" y="{top:.1f}" width="{BOXW}" height="{h}" rx="5" '
        f'fill="#eff6ff" stroke="{SEEDTAG}" stroke-width="1.5"/>'
        f'<text x="{x + BOXW/2:.1f}" y="{cy + 4:.1f}" text-anchor="middle" '
        f'font-family="system-ui,Arial" font-size="12" font-weight="700" '
        f'fill="{SEEDTAG}">{g["top"]}</text>'
    )

def _connector(src, dst, slot):
    """Elbow from src game's right-center to dst game's given slot (top/bottom).
    A single-slot box (champion) connects at its center, so an aligned feeder
    draws a straight line."""
    fx = _x(src["col"]) + BOXW
    fy = _cy(src["lane"])
    tx = _x(dst["col"])
    if dst.get("single"):
        ty = _cy(dst["lane"])
    else:
        ty = _cy(dst["lane"]) + (-ROWU/2 if slot == "top" else ROWU/2)
    midx = (fx + tx) / 2
    return "\n".join([
        f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{midx:.1f}" y2="{fy:.1f}" stroke="{LINE}" stroke-width="1.5"/>',
        f'<line x1="{midx:.1f}" y1="{fy:.1f}" x2="{midx:.1f}" y2="{ty:.1f}" stroke="{LINE}" stroke-width="1.5"/>',
        f'<line x1="{midx:.1f}" y1="{ty:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{LINE}" stroke-width="1.5"/>',
    ])

def draw(title, games, connectors):
    by_id = {g["id"]: g for g in games}
    max_col = max(g["col"] for g in games)
    max_lane = max(g["lane"] for g in games)
    width = _x(max_col) + BOXW + MARGIN_X
    height = _cy(max_lane) + ROWU + 30

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="{BG}"/>',
        f'<text x="{width/2:.1f}" y="26" text-anchor="middle" font-family="system-ui,Arial" '
        f'font-size="15" font-weight="700" fill="{TITLE}">{title}</text>',
    ]
    # connectors behind boxes
    for src_id, dst_id, slot in connectors:
        parts.append(_connector(by_id[src_id], by_id[dst_id], slot))
    # boxes
    for g in games:
        parts.append(_single_svg(g) if g.get("single") else _game_svg(g))
    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Format definitions: games on a (col, lane) grid + connector list
# Each connector = (source_game_id, dest_game_id, dest_slot)
# ---------------------------------------------------------------------------

DOUBLE_BYE = {
    "title": "10-Team Double Bye  (2027 Format)",
    "games": [
        {"id": "r1a", "col": 0, "lane": 0, "top": "Seed 3", "bottom": "Seed 10"},
        {"id": "r1b", "col": 0, "lane": 1, "top": "Seed 6", "bottom": "Seed 7"},
        {"id": "r1c", "col": 0, "lane": 2, "top": "Seed 4", "bottom": "Seed 9"},
        {"id": "r1d", "col": 0, "lane": 3, "top": "Seed 5", "bottom": "Seed 8"},
        {"id": "qf1", "col": 1, "lane": 0.5, "top": "", "bottom": ""},
        {"id": "qf2", "col": 1, "lane": 2.5, "top": "", "bottom": ""},
        {"id": "sf1", "col": 2, "lane": 0.5, "top": "Seed 1 (bye)", "bottom": ""},
        {"id": "sf2", "col": 2, "lane": 2.5, "top": "Seed 2 (bye)", "bottom": ""},
        {"id": "fin", "col": 3, "lane": 1.5, "top": "", "bottom": ""},
        {"id": "champ", "col": 4, "lane": 1.5, "top": "Champion", "single": True},
    ],
    "connectors": [
        ("r1a", "qf1", "top"), ("r1b", "qf1", "bottom"),
        ("r1c", "qf2", "top"), ("r1d", "qf2", "bottom"),
        ("qf1", "sf1", "bottom"),
        ("qf2", "sf2", "bottom"),
        ("sf1", "fin", "top"), ("sf2", "fin", "bottom"),
        ("fin", "champ", "top"),
    ],
}

NO_BYES = {
    "title": "8-Team No Byes",
    "games": [
        {"id": "r1a", "col": 0, "lane": 0, "top": "Seed 1", "bottom": "Seed 8"},
        {"id": "r1b", "col": 0, "lane": 1, "top": "Seed 4", "bottom": "Seed 5"},
        {"id": "r1c", "col": 0, "lane": 2, "top": "Seed 2", "bottom": "Seed 7"},
        {"id": "r1d", "col": 0, "lane": 3, "top": "Seed 3", "bottom": "Seed 6"},
        {"id": "sf1", "col": 1, "lane": 0.5, "top": "", "bottom": ""},
        {"id": "sf2", "col": 1, "lane": 2.5, "top": "", "bottom": ""},
        {"id": "fin", "col": 2, "lane": 1.5, "top": "", "bottom": ""},
        {"id": "champ", "col": 3, "lane": 1.5, "top": "Champion", "single": True},
    ],
    "connectors": [
        ("r1a", "sf1", "top"), ("r1b", "sf1", "bottom"),
        ("r1c", "sf2", "top"), ("r1d", "sf2", "bottom"),
        ("sf1", "fin", "top"), ("sf2", "fin", "bottom"),
        ("fin", "champ", "top"),
    ],
}

SIX_BYES = {
    "title": "10-Team Six Single Byes  (Current Format)",
    "games": [
        # opening round (seeds 7-10), placed at the bottom slot of their QF
        {"id": "o1", "col": 0, "lane": 0.5, "top": "Seed 8", "bottom": "Seed 9"},
        {"id": "o2", "col": 0, "lane": 3.5, "top": "Seed 7", "bottom": "Seed 10"},
        {"id": "qf1", "col": 1, "lane": 0, "top": "Seed 1 (bye)", "bottom": ""},
        {"id": "qf2", "col": 1, "lane": 1, "top": "Seed 4", "bottom": "Seed 5"},
        {"id": "qf3", "col": 1, "lane": 2, "top": "Seed 3", "bottom": "Seed 6"},
        {"id": "qf4", "col": 1, "lane": 3, "top": "Seed 2 (bye)", "bottom": ""},
        {"id": "sf1", "col": 2, "lane": 0.5, "top": "", "bottom": ""},
        {"id": "sf2", "col": 2, "lane": 2.5, "top": "", "bottom": ""},
        {"id": "fin", "col": 3, "lane": 1.5, "top": "", "bottom": ""},
        {"id": "champ", "col": 4, "lane": 1.5, "top": "Champion", "single": True},
    ],
    "connectors": [
        ("o1", "qf1", "bottom"),
        ("o2", "qf4", "bottom"),
        ("qf1", "sf1", "top"), ("qf2", "sf1", "bottom"),
        ("qf3", "sf2", "top"), ("qf4", "sf2", "bottom"),
        ("sf1", "fin", "top"), ("sf2", "fin", "bottom"),
        ("fin", "champ", "top"),
    ],
}

# Same QF structure as SIX_BYES but SF matchups are determined by reseeding after QF.
# The 4 QF winners are reseeded 1-4 by original seed: best vs worst, 2nd vs 3rd.
# No pre-drawn QF→SF connectors; SF boxes show reseed labels instead.
SIX_BYES_RESEEDED = {
    "title": "10-Team, 6 Byes + Reseed after QF",
    "games": [
        {"id": "o1", "col": 0, "lane": 0.5, "top": "Seed 8", "bottom": "Seed 9"},
        {"id": "o2", "col": 0, "lane": 3.5, "top": "Seed 7", "bottom": "Seed 10"},
        {"id": "qf1", "col": 1, "lane": 0, "top": "Seed 1 (bye)", "bottom": ""},
        {"id": "qf2", "col": 1, "lane": 1, "top": "Seed 4", "bottom": "Seed 5"},
        {"id": "qf3", "col": 1, "lane": 2, "top": "Seed 3", "bottom": "Seed 6"},
        {"id": "qf4", "col": 1, "lane": 3, "top": "Seed 2 (bye)", "bottom": ""},
        {"id": "sf1", "col": 2, "lane": 0.5, "top": "Top seed left", "bottom": "Bottom seed left",
         "top_seed": False, "bottom_seed": False},
        {"id": "sf2", "col": 2, "lane": 2.5, "top": "2nd seed left", "bottom": "3rd seed left",
         "top_seed": False, "bottom_seed": False},
        {"id": "fin", "col": 3, "lane": 1.5, "top": "", "bottom": ""},
        {"id": "champ", "col": 4, "lane": 1.5, "top": "Champion", "single": True},
    ],
    "connectors": [
        # Opening → QF (same as SIX_BYES)
        ("o1", "qf1", "bottom"),
        ("o2", "qf4", "bottom"),
        # No QF→SF connectors (reseeding means SF matchups are determined after QF)
        ("sf1", "fin", "top"), ("sf2", "fin", "bottom"),
        ("fin", "champ", "top"),
    ],
}

BRACKETS = {
    "double_bye": DOUBLE_BYE,
    "no_byes": NO_BYES,
    "six_byes": SIX_BYES,
    "six_byes_reseeded": SIX_BYES_RESEEDED,
}

def main():
    out_dir = os.path.join("docs", "brackets")
    os.makedirs(out_dir, exist_ok=True)
    for name, spec in BRACKETS.items():
        svg = draw(spec["title"], spec["games"], spec["connectors"])
        path = os.path.join(out_dir, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        assert svg.strip().endswith("</svg>") and len(svg) > 200, f"bad svg: {name}"
        print(f"Wrote {path}")

if __name__ == "__main__":
    main()
