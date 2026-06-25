"""
Arch Madness bracket simulator.
Compares three bracket formats using T-Rank efficiency margin win probabilities.

Usage:
    python simulate.py [year] [--sims N]
    python simulate.py 2025
    python simulate.py 2025 --sims 50000
"""
import csv
import math
import random
import argparse
from collections import defaultdict

# ---------------------------------------------------------------------------
# Win probability
# ---------------------------------------------------------------------------

def _norm_cdf(x):
    """Standard normal CDF (pure Python, no scipy required)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def win_prob(em_a, t_a, em_b, t_b):
    """P(team A beats team B) on a neutral court."""
    avg_pace = (t_a + t_b) / 2
    sigma = 11.9 * math.sqrt(avg_pace / 67.5)
    return _norm_cdf((em_a - em_b) / sigma)

def sim_game(team_a, team_b):
    """Return winner of a single game."""
    p = win_prob(team_a["adj_em"], team_a["adj_t"], team_b["adj_em"], team_b["adj_t"])
    return team_a if random.random() < p else team_b

# ---------------------------------------------------------------------------
# Bracket formats
# ---------------------------------------------------------------------------

def bracket_10_double_bye(teams):
    """
    10-team bracket, seeds 1-2 get semifinal byes (new MVC 2027 format).

    R1 (Opening):  3v10, 4v9, 5v8, 6v7
    R2 (Quarters): W(3/10) vs W(6/7),  W(4/9) vs W(5/8)
    SF:            Seed1 vs R2-winner,  Seed2 vs R2-winner
    Final
    """
    s = {t["seed"]: t for t in teams}

    # R1
    w3  = sim_game(s[3],  s[10])
    w4  = sim_game(s[4],  s[9])
    w5  = sim_game(s[5],  s[8])
    w6  = sim_game(s[6],  s[7])

    # R2
    wq1 = sim_game(w3, w6)
    wq2 = sim_game(w4, w5)

    # SF
    wsf1 = sim_game(s[1], wq1)
    wsf2 = sim_game(s[2], wq2)

    # Final
    return sim_game(wsf1, wsf2)


def bracket_8_no_byes(teams):
    """
    8-team bracket, no byes (top 8 seeds only).

    R1: 1v8, 2v7, 3v6, 4v5
    SF: W(1/8) vs W(4/5),  W(2/7) vs W(3/6)
    Final
    """
    s = {t["seed"]: t for t in teams if t["seed"] <= 8}

    w1 = sim_game(s[1], s[8])
    w2 = sim_game(s[2], s[7])
    w3 = sim_game(s[3], s[6])
    w4 = sim_game(s[4], s[5])

    wsf1 = sim_game(w1, w4)
    wsf2 = sim_game(w2, w3)

    return sim_game(wsf1, wsf2)


def bracket_10_six_byes(teams):
    """
    10-team bracket, seeds 1-6 get quarterfinal byes (current MVC format adapted to 10 teams).

    Opening:   7v10, 8v9
    QF:        1 vs W(8/9),  2 vs W(7/10),  3v6,  4v5
    SF:        W(1-side) vs W(4/5),  W(2-side) vs W(3/6)
    Final
    """
    s = {t["seed"]: t for t in teams}

    # Opening
    w7  = sim_game(s[7],  s[10])
    w8  = sim_game(s[8],  s[9])

    # QF
    wq1 = sim_game(s[1], w8)
    wq2 = sim_game(s[2], w7)
    wq3 = sim_game(s[3], s[6])
    wq4 = sim_game(s[4], s[5])

    # SF
    wsf1 = sim_game(wq1, wq4)
    wsf2 = sim_game(wq2, wq3)

    return sim_game(wsf1, wsf2)


def bracket_10_six_byes_reseeded(teams):
    """
    Same as bracket_10_six_byes through the quarterfinals, then the 4 QF
    winners are reseeded 1-4 by original seed before the semifinals.
    Best remaining seed plays worst, 2nd plays 3rd.
    """
    s = {t["seed"]: t for t in teams}

    # Opening
    w7  = sim_game(s[7],  s[10])
    w8  = sim_game(s[8],  s[9])

    # QF (same as six_byes)
    wq1 = sim_game(s[1], w8)
    wq2 = sim_game(s[2], w7)
    wq3 = sim_game(s[3], s[6])
    wq4 = sim_game(s[4], s[5])

    # Reseed: sort by original seed, best (lowest number) vs worst
    r1, r2, r3, r4 = sorted([wq1, wq2, wq3, wq4], key=lambda t: t["seed"])
    wsf1 = sim_game(r1, r4)
    wsf2 = sim_game(r2, r3)

    return sim_game(wsf1, wsf2)


FORMATS = {
    "10-team double bye":      bracket_10_double_bye,
    "8-team no byes":          bracket_8_no_byes,
    "10-team 6 single byes":   bracket_10_six_byes,
    "10-team 6 byes reseeded": bracket_10_six_byes_reseeded,
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_teams(year):
    # Load actual MVC tournament seeds
    seeds = {}
    with open("data/arch_madness_seeds.csv") as f:
        for row in csv.DictReader(f):
            if int(row["year"]) == year:
                seeds[row["team"].strip().lower()] = int(row["seed"])

    teams = []
    with open("data/trank_mvc.csv") as f:
        for row in csv.DictReader(f):
            if int(row["year"]) != year:
                continue
            teams.append({
                "team":   row["team"],
                "trank":  float(row["trank"]),
                "adj_em": float(row["adj_em"]),
                "adj_t":  float(row["adj_t"]),
                "record": row["record"],
                "seed":   None,
            })

    # Match seeds by name (fuzzy: check if seed name is contained in trank name or vice versa)
    unmatched_seeds = dict(seeds)
    for t in teams:
        tname = t["team"].lower()
        for sname, seed in seeds.items():
            if sname in tname or tname in sname or _name_match(tname, sname):
                t["seed"] = seed
                unmatched_seeds.pop(sname, None)
                break

    # Fallback: assign remaining seeds by AdjEM rank for unmatched teams
    unseeded = [t for t in teams if t["seed"] is None]
    if unseeded:
        taken = {t["seed"] for t in teams if t["seed"]}
        available = sorted(s for s in range(1, len(teams) + 1) if s not in taken)
        unseeded.sort(key=lambda t: t["adj_em"], reverse=True)
        for t, s in zip(unseeded, available):
            t["seed"] = s

    if unmatched_seeds:
        print(f"  WARNING: unmatched seed names: {list(unmatched_seeds.keys())}")

    teams.sort(key=lambda t: t["seed"])
    return teams


def _name_match(a, b):
    """Catch common MVC name variations."""
    aliases = {
        "illinois chicago": "illinois chicago",
        "uic": "illinois chicago",
        "northern iowa": "northern iowa",
        "uni": "northern iowa",
        "southern illinois": "southern illinois",
        "siu": "southern illinois",
        "illinois st.": "illinois state",
        "illinois state": "illinois state",
        "loyola chicago": "loyola chicago",
        "loyola": "loyola chicago",
        "wichita st.": "wichita state",
        "wichita state": "wichita state",
        "murray st.": "murray state",
        "murray state": "murray state",
        "indiana st.": "indiana state",
        "indiana state": "indiana state",
        "missouri st.": "missouri state",
        "missouri state": "missouri state",
        "valparaiso": "valparaiso",
        "belmont": "belmont",
        "bradley": "bradley",
        "drake": "drake",
        "evansville": "evansville",
    }
    return aliases.get(a) == aliases.get(b) and aliases.get(a) is not None

# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_format(teams, bracket_fn, n_sims):
    wins = defaultdict(int)
    for _ in range(n_sims):
        winner = bracket_fn(teams)
        wins[winner["team"]] += 1
    return wins

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def pct(n, total):
    return f"{100 * n / total:.1f}%"

def print_table(teams, results, n_sims, format_names):
    # Header
    col_w = 22
    seed_w = 5
    trank_w = 7
    pct_w = 18

    header = f"{'Seed':>{seed_w}}  {'T-Rank':>{trank_w}}  {'Team':<{col_w}}  {'AdjEM':>6}  {'AdjT':>5}"
    for name in format_names:
        header += f"  {name:>{pct_w}}"
    print(header)
    print("-" * len(header))

    for t in teams:
        row = f"{t['seed']:>{seed_w}}  {t['trank']:>{trank_w}.0f}  {t['team']:<{col_w}}  {t['adj_em']:>+6.1f}  {t['adj_t']:>5.1f}"
        for name in format_names:
            w = results[name].get(t["team"], 0)
            row += f"  {pct(w, n_sims):>{pct_w}}"
        print(row)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, nargs="?", default=2025)
    parser.add_argument("--sims", type=int, default=10000)
    args = parser.parse_args()

    teams = load_teams(args.year)
    print(f"\nArch Madness Simulation — {args.year}  ({args.sims:,} simulations)\n")

    results = {}
    for name, fn in FORMATS.items():
        results[name] = run_format(teams, fn, args.sims)

    print_table(teams, results, args.sims, list(FORMATS.keys()))
    print()

if __name__ == "__main__":
    main()
