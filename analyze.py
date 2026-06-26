"""
Arch Madness full analysis across all years and bracket formats.

Outputs:
  data/simulations_raw.csv     — every individual simulation result
  data/simulation_summary.csv  — win % per team per year per format
  data/analysis_by_year.csv    — did the best/top-seed/model-pick win?

Usage:
    python analyze.py [--sims N]
"""
import csv
import math
import random
import argparse
from collections import defaultdict

# ---------------------------------------------------------------------------
# Re-use core logic from simulate.py
# ---------------------------------------------------------------------------

def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def win_prob(em_a, t_a, em_b, t_b):
    avg_pace = (t_a + t_b) / 2
    sigma = 11.9 * math.sqrt(avg_pace / 67.5)
    return _norm_cdf((em_a - em_b) / sigma)

def sim_game(a, b):
    p = win_prob(a["adj_em"], a["adj_t"], b["adj_em"], b["adj_t"])
    return a if random.random() < p else b

def bracket_10_double_bye(s):
    w3  = sim_game(s[3],  s[10])
    w4  = sim_game(s[4],  s[9])
    w5  = sim_game(s[5],  s[8])
    w6  = sim_game(s[6],  s[7])
    wq1 = sim_game(w3, w6)
    wq2 = sim_game(w4, w5)
    wsf1 = sim_game(s[1], wq1)
    wsf2 = sim_game(s[2], wq2)
    return sim_game(wsf1, wsf2)

def bracket_8_no_byes(s):
    w1 = sim_game(s[1], s[8])
    w2 = sim_game(s[2], s[7])
    w3 = sim_game(s[3], s[6])
    w4 = sim_game(s[4], s[5])
    wsf1 = sim_game(w1, w4)
    wsf2 = sim_game(w2, w3)
    return sim_game(wsf1, wsf2)

def bracket_10_six_byes(s):
    w7  = sim_game(s[7],  s[10])
    w8  = sim_game(s[8],  s[9])
    wq1 = sim_game(s[1], w8)
    wq2 = sim_game(s[2], w7)
    wq3 = sim_game(s[3], s[6])
    wq4 = sim_game(s[4], s[5])
    wsf1 = sim_game(wq1, wq4)
    wsf2 = sim_game(wq2, wq3)
    return sim_game(wsf1, wsf2)

def bracket_10_six_byes_reseeded(s):
    w7  = sim_game(s[7],  s[10])
    w8  = sim_game(s[8],  s[9])
    wq1 = sim_game(s[1], w8)
    wq2 = sim_game(s[2], w7)
    wq3 = sim_game(s[3], s[6])
    wq4 = sim_game(s[4], s[5])
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

YEARS = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026]

# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

ALIASES = {
    "illinois chicago": "illinois chicago",
    "uic":              "illinois chicago",
    "northern iowa":    "northern iowa",
    "uni":              "northern iowa",
    "southern illinois":"southern illinois",
    "siu":              "southern illinois",
    "illinois st.":     "illinois state",
    "illinois state":   "illinois state",
    "loyola chicago":   "loyola chicago",
    "loyola":           "loyola chicago",
    "wichita st.":      "wichita state",
    "wichita state":    "wichita state",
    "murray st.":       "murray state",
    "murray state":     "murray state",
    "indiana st.":      "indiana state",
    "indiana state":    "indiana state",
    "missouri st.":     "missouri state",
    "missouri state":   "missouri state",
    "valparaiso":       "valparaiso",
    "belmont":          "belmont",
    "bradley":          "bradley",
    "drake":            "drake",
    "evansville":       "evansville",
}

def normalize(name):
    return ALIASES.get(name.strip().lower(), name.strip().lower())

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_seeds(year):
    seeds = {}
    with open("data/arch_madness_seeds.csv") as f:
        for row in csv.DictReader(f):
            if int(row["year"]) == year:
                seeds[normalize(row["team"])] = int(row["seed"])
    return seeds

def load_champions():
    champs = {}
    with open("data/arch_madness_champions.csv") as f:
        for row in csv.DictReader(f):
            champs[int(row["year"])] = {
                "champion":      normalize(row["champion"]),
                "champion_seed": int(row["champion_seed"]) if row["champion_seed"] else None,
            }
    return champs

def load_teams(year):
    seed_map = load_seeds(year)

    teams = []
    with open("data/trank_mvc.csv") as f:
        for row in csv.DictReader(f):
            if int(row["year"]) != year:
                continue
            teams.append({
                "team":    row["team"],
                "norm":    normalize(row["team"]),
                "trank":   float(row["trank"]),
                "adj_em":  float(row["adj_em"]),
                "adj_t":   float(row["adj_t"]),
                "record":  row["record"],
                "seed":    None,
            })

    # Assign seeds
    taken = set()
    for t in teams:
        if t["norm"] in seed_map:
            t["seed"] = seed_map[t["norm"]]
            taken.add(t["norm"])

    # Fallback for unmatched
    unseeded = [t for t in teams if t["seed"] is None]
    if unseeded:
        used = {t["seed"] for t in teams if t["seed"]}
        available = sorted(s for s in range(1, len(teams) + 1) if s not in used)
        unseeded.sort(key=lambda t: t["adj_em"], reverse=True)
        for t, s in zip(unseeded, available):
            t["seed"] = s

    teams.sort(key=lambda t: t["seed"])
    return teams

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_sims(teams, bracket_fn, n_sims):
    """Returns list of winner dicts (one per sim)."""
    s = {t["seed"]: t for t in teams}
    results = []
    for i in range(n_sims):
        winner = bracket_fn(s)
        results.append(winner)
    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", type=int, default=10000)
    args = parser.parse_args()

    champions = load_champions()

    raw_rows = []        # every sim
    summary_rows = []    # win % per team per year per format
    analysis_rows = []   # one row per year per format

    for year in YEARS:
        teams = load_teams(year)
        actual_champ = champions.get(year, {}).get("champion")
        n = len(teams)
        print(f"\n{year}  ({n} teams)  actual champion: {actual_champ}")

        # Who is "best" by each definition?
        best_adjEM = max(teams, key=lambda t: t["adj_em"])
        best_trank = min(teams, key=lambda t: t["trank"])
        top_seed   = next(t for t in teams if t["seed"] == 1)

        for fmt_name, fmt_fn in FORMATS.items():
            # Only run formats that fit team count
            max_seed_needed = 10 if "10-team" in fmt_name else 8
            if n < max_seed_needed:
                print(f"  SKIP {fmt_name} — only {n} teams")
                continue

            sims = run_sims(teams, fmt_fn, args.sims)

            # Count wins per team
            win_counts = defaultdict(int)
            for w in sims:
                win_counts[w["norm"]] += 1

            # Save raw sims
            for i, w in enumerate(sims):
                raw_rows.append({
                    "year":         year,
                    "format":       fmt_name,
                    "sim":          i + 1,
                    "winner_team":  w["team"],
                    "winner_seed":  w["seed"],
                    "winner_trank": w["trank"],
                    "winner_adjEM": w["adj_em"],
                })

            # Save summary
            for t in teams:
                w = win_counts.get(t["norm"], 0)
                summary_rows.append({
                    "year":        year,
                    "format":      fmt_name,
                    "team":        t["team"],
                    "seed":        t["seed"],
                    "trank":       t["trank"],
                    "adj_em":      t["adj_em"],
                    "adj_t":       t["adj_t"],
                    "win_count":   w,
                    "win_pct":     round(100 * w / args.sims, 2),
                    "actual_champion": 1 if t["norm"] == actual_champ else 0,
                })

            # Analysis row
            model_pick = max(teams[:max_seed_needed], key=lambda t: win_counts.get(t["norm"], 0))
            actual_team = next((t for t in teams if t["norm"] == actual_champ), None)
            actual_win_pct = round(100 * win_counts.get(actual_champ, 0) / args.sims, 2) if actual_champ else None
            model_correct = (normalize(model_pick["team"]) == actual_champ) if actual_champ else None

            analysis_rows.append({
                "year":                  year,
                "format":                fmt_name,
                "top_adjEM_team":        best_adjEM["team"],
                "top_adjEM_seed":        best_adjEM["seed"],
                "top_adjEM_win_pct":     round(100 * win_counts.get(best_adjEM["norm"], 0) / args.sims, 2),
                "top_trank_team":        best_trank["team"],
                "top_trank_seed":        best_trank["seed"],
                "top_trank_win_pct":     round(100 * win_counts.get(best_trank["norm"], 0) / args.sims, 2),
                "top_seed_team":         top_seed["team"],
                "top_seed_adjEM":        top_seed["adj_em"],
                "top_seed_win_pct":      round(100 * win_counts.get(top_seed["norm"], 0) / args.sims, 2),
                "model_pick_team":       model_pick["team"],
                "model_pick_seed":       model_pick["seed"],
                "model_pick_win_pct":    round(100 * win_counts.get(model_pick["norm"], 0) / args.sims, 2),
                "actual_champion":       actual_champ,
                "actual_champion_seed":  actual_team["seed"] if actual_team else None,
                "actual_champion_adjEM": actual_team["adj_em"] if actual_team else None,
                "actual_champion_trank": actual_team["trank"] if actual_team else None,
                "actual_sim_win_pct":    actual_win_pct,
                "model_correct":         int(model_correct) if model_correct is not None else "",
            })

            correct = "Y" if model_correct else "N"
            print(f"  {fmt_name:<24}  model: {model_pick['team']} ({model_pick['adj_em']:+.1f}) {win_counts.get(model_pick['norm'],0)/args.sims*100:.1f}%  actual: {actual_champ} {actual_win_pct}%  {correct}")

    # Write CSVs
    with open("data/simulations_raw.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=raw_rows[0].keys())
        w.writeheader(); w.writerows(raw_rows)

    with open("data/simulation_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        w.writeheader(); w.writerows(summary_rows)

    with open("data/analysis_by_year.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=analysis_rows[0].keys())
        w.writeheader(); w.writerows(analysis_rows)

    print(f"\nSaved:")
    print(f"  data/simulations_raw.csv     ({len(raw_rows):,} rows)")
    print(f"  data/simulation_summary.csv  ({len(summary_rows):,} rows)")
    print(f"  data/analysis_by_year.csv    ({len(analysis_rows):,} rows)")

    # Print summary table
    print("\n\n=== MODEL ACCURACY SUMMARY ===\n")
    print(f"{'Year':<6} {'Format':<26} {'Top AdjEM':<20} {'Top Seed':<20} {'Model Pick':<20} {'Actual Champion':<20} {'Champ%':>7} {'Correct':>8}")
    print("-" * 135)
    for r in analysis_rows:
        correct = "Y" if r["model_correct"] == 1 else ("N" if r["model_correct"] == 0 else "?")
        print(f"{r['year']:<6} {r['format']:<26} {r['top_adjEM_team']:<20} {r['top_seed_team']:<20} {r['model_pick_team']:<20} {str(r['actual_champion']):<20} {str(r['actual_sim_win_pct']):>7}% {correct:>8}")

if __name__ == "__main__":
    main()
