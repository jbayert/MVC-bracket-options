"""
Bad losses: when a top-2 seed is eliminated by a team ranked worse than 100
(T-Rank number > 100).

Writes:
  data/bad_losses_sim.csv     — simulated bad-loss / normal-loss / title % per
                                year, format, top seed
  data/bad_losses_actual.csv  — actual historical outcome for each top-2 seed,
                                joined to the eliminator's rank (needs
                                data/top_seed_exits.csv)

Reuses team/seed/champion loaders and YEARS from analyze.py.

Usage:
    python bad_losses.py [--sims N]
"""
import csv
import math
import random
import argparse
from collections import defaultdict

from analyze import load_teams, normalize, YEARS

BAD_RANK = 100  # eliminator with trank > 100 = "bad loss"

# ---------------------------------------------------------------------------
# Win probability + elimination-tracking game
# ---------------------------------------------------------------------------

def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def win_prob(a, b):
    avg_pace = (a["adj_t"] + b["adj_t"]) / 2
    sigma = 11.9 * math.sqrt(avg_pace / 67.5)
    return _norm_cdf((a["adj_em"] - b["adj_em"]) / sigma)

def sim_game(a, b, elim):
    """Play a game; record elim[loser_seed] = winner so we know who knocked a team out."""
    winner = a if random.random() < win_prob(a, b) else b
    loser = b if winner is a else a
    elim[loser["seed"]] = winner
    return winner

# ---------------------------------------------------------------------------
# Bracket variants (mirror analyze.py, but thread an `elim` dict)
# ---------------------------------------------------------------------------

def double_bye(s, e):
    w3 = sim_game(s[3], s[10], e); w4 = sim_game(s[4], s[9], e)
    w5 = sim_game(s[5], s[8], e);  w6 = sim_game(s[6], s[7], e)
    wq1 = sim_game(w3, w6, e); wq2 = sim_game(w4, w5, e)
    wsf1 = sim_game(s[1], wq1, e); wsf2 = sim_game(s[2], wq2, e)
    return sim_game(wsf1, wsf2, e)

def no_byes(s, e):
    w1 = sim_game(s[1], s[8], e); w2 = sim_game(s[2], s[7], e)
    w3 = sim_game(s[3], s[6], e); w4 = sim_game(s[4], s[5], e)
    wsf1 = sim_game(w1, w4, e); wsf2 = sim_game(w2, w3, e)
    return sim_game(wsf1, wsf2, e)

def six_byes(s, e):
    w7 = sim_game(s[7], s[10], e); w8 = sim_game(s[8], s[9], e)
    wq1 = sim_game(s[1], w8, e); wq2 = sim_game(s[2], w7, e)
    wq3 = sim_game(s[3], s[6], e); wq4 = sim_game(s[4], s[5], e)
    wsf1 = sim_game(wq1, wq4, e); wsf2 = sim_game(wq2, wq3, e)
    return sim_game(wsf1, wsf2, e)

def six_byes_reseeded(s, e):
    w7 = sim_game(s[7], s[10], e); w8 = sim_game(s[8], s[9], e)
    wq1 = sim_game(s[1], w8, e); wq2 = sim_game(s[2], w7, e)
    wq3 = sim_game(s[3], s[6], e); wq4 = sim_game(s[4], s[5], e)
    r1, r2, r3, r4 = sorted([wq1, wq2, wq3, wq4], key=lambda t: t["seed"])
    wsf1 = sim_game(r1, r4, e); wsf2 = sim_game(r2, r3, e)
    return sim_game(wsf1, wsf2, e)

FORMATS = {
    "10-team double bye":      double_bye,
    "8-team no byes":          no_byes,
    "10-team 6 single byes":   six_byes,
    "10-team 6 byes reseeded": six_byes_reseeded,
}

# ---------------------------------------------------------------------------
# Simulated bad losses
# ---------------------------------------------------------------------------

def simulate(year, fmt_fn, n_sims):
    teams = load_teams(year)
    s = {t["seed"]: t for t in teams}
    # counts[seed] = {bad, normal, title}
    counts = {1: defaultdict(int), 2: defaultdict(int)}
    for _ in range(n_sims):
        elim = {}
        fmt_fn(s, elim)
        for seed in (1, 2):
            if seed not in elim:
                counts[seed]["title"] += 1
            elif elim[seed]["trank"] > BAD_RANK:
                counts[seed]["bad"] += 1
            else:
                counts[seed]["normal"] += 1
    return counts

def run_sim(n_sims):
    rows = []
    for year in YEARS:
        for fmt_name, fmt_fn in FORMATS.items():
            counts = simulate(year, fmt_fn, n_sims)
            for seed in (1, 2):
                c = counts[seed]
                bad = round(100 * c["bad"] / n_sims, 1)
                normal = round(100 * c["normal"] / n_sims, 1)
                title = round(100 * c["title"] / n_sims, 1)
                assert abs(bad + normal + title - 100) < 0.2, (year, fmt_name, seed)
                rows.append({"year": year, "format": fmt_name, "seed": seed,
                             "bad_loss_pct": bad, "normal_loss_pct": normal,
                             "title_pct": title})
    with open("data/bad_losses_sim.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"Wrote data/bad_losses_sim.csv ({len(rows)} rows)")
    return rows

# ---------------------------------------------------------------------------
# Actual bad losses (needs data/top_seed_exits.csv)
# ---------------------------------------------------------------------------

def trank_lookup():
    """(year, normalized team) -> national trank."""
    lut = {}
    with open("data/trank_mvc.csv") as f:
        for r in csv.DictReader(f):
            lut[(int(r["year"]), normalize(r["team"]))] = int(float(r["trank"]))
    return lut

def run_actual():
    try:
        with open("data/top_seed_exits.csv") as f:
            exits = list(csv.DictReader(f))
    except FileNotFoundError:
        print("SKIP actual — data/top_seed_exits.csv not found yet")
        return None

    lut = trank_lookup()
    rows = []
    for r in exits:
        year = int(r["year"])
        team = r["team"]
        elim_by = r["eliminated_by"].strip()
        won = (elim_by == "")
        team_trank = lut.get((year, normalize(team)))
        elim_trank = None if won else lut.get((year, normalize(elim_by)))
        bad = int((not won) and elim_trank is not None and elim_trank > BAD_RANK)
        rows.append({
            "year": year, "seed": int(r["seed"]), "team": team,
            "team_trank": team_trank, "won_title": int(won),
            "eliminated_by": elim_by, "eliminated_by_trank": elim_trank,
            "round": r.get("round", ""), "bad_loss": bad,
        })
    with open("data/bad_losses_actual.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"Wrote data/bad_losses_actual.csv ({len(rows)} rows)")
    return rows

# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=10000)
    args = ap.parse_args()

    sim_rows = run_sim(args.sims)
    run_actual()

    # Summary: average simulated bad-loss % per format (both top seeds)
    print(f"\nAverage simulated bad-loss % (top-2 seeds), {args.sims:,} sims:")
    agg = defaultdict(list)
    for r in sim_rows:
        agg[r["format"]].append(r["bad_loss_pct"])
    for fmt, vals in agg.items():
        print(f"  {fmt:<26} {sum(vals)/len(vals):5.1f}%")

if __name__ == "__main__":
    main()
