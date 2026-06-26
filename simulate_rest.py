"""
Rest-aware bracket simulation.

Adds a rest/fatigue term to the base efficiency-margin model and compares
championship odds and model accuracy WITH vs WITHOUT the rest adjustment,
across every year and bracket format.

See design/rest_model.md for the methodology and coefficients.

Usage:
    python simulate_rest.py [--sims N]
"""
import csv
import math
import random
import argparse
from collections import defaultdict

# --- Rest model coefficients (see design/rest_model.md) ---
REST_COEFF = 2.5      # points per extra rest day
FATIGUE_COEFF = 0.75  # points lost per extra game already played
REST_CAP = 3          # max rest days credited (caps pre-tournament layoff)
FRESH = REST_CAP      # rest credited to a team's first game

YEARS = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026]

# ---------------------------------------------------------------------------
# Win probability (base + optional rest term)
# ---------------------------------------------------------------------------

def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def win_prob(a, b, rest=False):
    """P(a beats b). a, b are dicts with adj_em, adj_t, and (if rest) rest_days, games."""
    avg_pace = (a["adj_t"] + b["adj_t"]) / 2
    sigma = 11.9 * math.sqrt(avg_pace / 67.5)
    margin = a["adj_em"] - b["adj_em"]
    if rest:
        margin += REST_COEFF * (a["rest_days"] - b["rest_days"])
        margin -= FATIGUE_COEFF * (a["games"] - b["games"])
    return _norm_cdf(margin / sigma)

# ---------------------------------------------------------------------------
# Bracket as a tree. A node is either a seed int (leaf) or a Game.
# Game(top, bottom, day): the two feeders and the calendar day it is played.
# ---------------------------------------------------------------------------

class Game:
    __slots__ = ("top", "bottom", "day")
    def __init__(self, top, bottom, day):
        self.top, self.bottom, self.day = top, bottom, day

def _resolve(node, teams_by_seed, rest):
    """
    Return a competitor dict carrying rest/fatigue state.
    Leaf (seed int): fresh team. Game: simulate it and return the winner.
    """
    if isinstance(node, int):
        t = dict(teams_by_seed[node])
        t["games"] = 0
        t["last_day"] = None
        return t

    a = _resolve(node.top, teams_by_seed, rest)
    b = _resolve(node.bottom, teams_by_seed, rest)

    for t in (a, b):
        last = t["last_day"]
        t["rest_days"] = FRESH if last is None else min(REST_CAP, node.day - last)

    winner = a if random.random() < win_prob(a, b, rest) else b
    winner = dict(winner)
    winner["games"] += 1
    winner["last_day"] = node.day
    return winner

def G(top, bottom, day):
    return Game(top, bottom, day)

# Bracket trees (days 1..4, one round per day)
def double_bye():
    return G(
        G(1, G(G(3, 10, 1), G(6, 7, 1), 2), 3),
        G(2, G(G(4, 9, 1), G(5, 8, 1), 2), 3),
        4)

def no_byes():
    return G(
        G(G(1, 8, 1), G(4, 5, 1), 2),
        G(G(2, 7, 1), G(3, 6, 1), 2),
        3)

def six_byes():
    return G(
        G(G(1, G(8, 9, 1), 2), G(4, 5, 2), 3),
        G(G(2, G(7, 10, 1), 2), G(3, 6, 2), 3),
        4)

FORMATS = {
    "10-team double bye": double_bye,
    "8-team no byes": no_byes,
    "10-team 6 single byes": six_byes,
}

# ---------------------------------------------------------------------------
# Data loading (seeds + T-Rank), mirrors analyze.py
# ---------------------------------------------------------------------------

ALIASES = {
    "illinois chicago": "illinois chicago", "uic": "illinois chicago",
    "northern iowa": "northern iowa", "uni": "northern iowa",
    "southern illinois": "southern illinois", "siu": "southern illinois",
    "illinois st.": "illinois state", "illinois state": "illinois state",
    "loyola chicago": "loyola chicago", "loyola": "loyola chicago",
    "wichita st.": "wichita state", "wichita state": "wichita state",
    "murray st.": "murray state", "murray state": "murray state",
    "indiana st.": "indiana state", "indiana state": "indiana state",
    "missouri st.": "missouri state", "missouri state": "missouri state",
    "valparaiso": "valparaiso", "belmont": "belmont", "bradley": "bradley",
    "drake": "drake", "evansville": "evansville",
}
def norm(n): return ALIASES.get(n.strip().lower(), n.strip().lower())

def load_year(year):
    seeds = {}
    with open("data/arch_madness_seeds.csv") as f:
        for r in csv.DictReader(f):
            if int(r["year"]) == year:
                seeds[norm(r["team"])] = int(r["seed"])

    teams = []
    with open("data/trank_mvc.csv") as f:
        for r in csv.DictReader(f):
            if int(r["year"]) != year:
                continue
            teams.append({"team": r["team"], "norm": norm(r["team"]),
                          "adj_em": float(r["adj_em"]), "adj_t": float(r["adj_t"]),
                          "seed": seeds.get(norm(r["team"]))})

    unseeded = [t for t in teams if t["seed"] is None]
    if unseeded:
        used = {t["seed"] for t in teams if t["seed"]}
        avail = sorted(s for s in range(1, len(teams) + 1) if s not in used)
        unseeded.sort(key=lambda t: t["adj_em"], reverse=True)
        for t, s in zip(unseeded, avail):
            t["seed"] = s

    return {t["seed"]: t for t in teams}

def load_champions():
    champs = {}
    with open("data/arch_madness_champions.csv") as f:
        for r in csv.DictReader(f):
            champs[int(r["year"])] = norm(r["champion"])
    return champs

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def simulate(year, fmt_fn, n_sims, rest):
    teams_by_seed = load_year(year)
    wins = defaultdict(int)
    for _ in range(n_sims):
        champ = _resolve(fmt_fn(), teams_by_seed, rest)
        wins[champ["norm"]] += 1
    return wins, teams_by_seed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=10000)
    args = ap.parse_args()

    champions = load_champions()
    rows = []
    acc = {fmt: {"base": 0, "rest": 0, "total": 0} for fmt in FORMATS}

    print(f"Rest model: REST_COEFF={REST_COEFF}, FATIGUE_COEFF={FATIGUE_COEFF}, "
          f"REST_CAP={REST_CAP}  ({args.sims:,} sims)\n")

    for year in YEARS:
        actual = champions[year]
        for fmt_name, fmt_fn in FORMATS.items():
            base_wins, teams = simulate(year, fmt_fn, args.sims, rest=False)
            rest_wins, _ = simulate(year, fmt_fn, args.sims, rest=True)

            def pick(wins):
                top = max(wins, key=wins.get)
                return top, round(100 * wins[top] / args.sims, 1)

            bp, bpct = pick(base_wins)
            rp, rpct = pick(rest_wins)
            base_ok = (bp == actual)
            rest_ok = (rp == actual)

            acc[fmt_name]["total"] += 1
            acc[fmt_name]["base"] += base_ok
            acc[fmt_name]["rest"] += rest_ok

            actual_base = round(100 * base_wins.get(actual, 0) / args.sims, 1)
            actual_rest = round(100 * rest_wins.get(actual, 0) / args.sims, 1)

            rows.append({
                "year": year, "format": fmt_name, "actual_champion": actual,
                "base_pick": bp, "base_pick_pct": bpct, "base_correct": int(base_ok),
                "rest_pick": rp, "rest_pick_pct": rpct, "rest_correct": int(rest_ok),
                "actual_base_pct": actual_base, "actual_rest_pct": actual_rest,
                "actual_pct_delta": round(actual_rest - actual_base, 1),
            })

    with open("data/rest_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)

    # Accuracy summary
    print("Model accuracy (top pick = actual champion):\n")
    print(f"{'Format':<26} {'Base':>8} {'+Rest':>8}")
    print("-" * 44)
    for fmt in FORMATS:
        a = acc[fmt]
        print(f"{fmt:<26} {a['base']}/{a['total']:<6} {a['rest']}/{a['total']:<6}")

    # How rest shifts the actual champion's odds
    print("\nEffect of rest on the ACTUAL champion's simulated title odds:")
    print(f"{'Year':<6} {'Format':<26} {'Champion':<16} {'Base%':>7} {'Rest%':>7} {'Delta':>7}")
    print("-" * 72)
    for r in rows:
        print(f"{r['year']:<6} {r['format']:<26} {r['actual_champion']:<16} "
              f"{r['actual_base_pct']:>6}% {r['actual_rest_pct']:>6}% {r['actual_pct_delta']:>+6}")

    print(f"\nWrote data/rest_comparison.csv ({len(rows)} rows)")

if __name__ == "__main__":
    main()
