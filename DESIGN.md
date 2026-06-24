# Arch Madness Bracket Simulator — Design

## Goal

Simulate the MVC tournament (Arch Madness) 10,000 times per year using team efficiency data to estimate each team's championship probability. Compare results across the old and new bracket formats to understand how the 2027 format change affects expected outcomes.

---

## Data

### Sources

| Data | Source | Years | Status |
|------|--------|-------|--------|
| T-Rank (AdjOE, AdjDE, AdjT, AdjEM) | barttorvik.com — saved as HTML, parsed to CSV | 2015–2026 (skip 2020) | ✅ Done |
| Tournament results (champions, scores) | Wikipedia / ESPN research | 2015–2025 (skip 2020) | ✅ Done |
| Full bracket results (all rounds) | Manual research | 2021–2025 complete; 2015–2019 partial | ⚠️ Partial |
| Team seeds per year | Manual research | 2023–2025 complete; earlier years missing | ⚠️ Partial |
| Betting odds | OddsPortal / Covers | Finals only for 2022, 2024 | ⚠️ Partial |

### Key Files

```
data/
  trank_mvc.csv              # T-Rank stats per team per year (117 rows)
  arch_madness_champions.csv # Champion + runner-up + final score per year
  arch_madness_bracket_results.csv  # Game-by-game results where available
  arch_madness_seeds.csv     # Tournament seeds per team per year
  arch_madness_format.csv    # Bracket format by era
```

### T-Rank Columns Used

- `adj_oe` — Adjusted offensive efficiency (points scored per 100 possessions, opponent-adjusted)
- `adj_de` — Adjusted defensive efficiency (points allowed per 100 possessions, opponent-adjusted)
- `adj_em` — Efficiency margin = adj_oe - adj_de (higher = better)
- `adj_t` — Adjusted tempo (possessions per 40 minutes)
- `seed` — MVC tournament seed (parsed from T-Rank HTML where available)

---

## Win Probability Model

### Formula

For a neutral-court game between Team A and Team B:

```
expected_margin = AdjEM_A - AdjEM_B

avg_pace = (AdjT_A + AdjT_B) / 2
sigma = 11.9 * sqrt(avg_pace / 67.5)

p_win_A = norm.cdf(expected_margin / sigma)
```

### Why This Works

- `expected_margin` is the points Team A is expected to win by, derived from season-long efficiency
- `sigma = 11.9` is the empirical standard deviation of college basketball game outcomes around the expected margin (calibrated by KenPom, confirmed by multiple studies at 11.5–12.0)
- Tempo scales sigma because more possessions = more absolute variance in score (`sqrt` of possessions)
- `norm.cdf` gives the probability that the actual margin (normally distributed) lands above 0

### Example

Drake 2024: AdjEM = +18, AdjT = 68
Indiana State 2024: AdjEM = +12, AdjT = 65

```
expected_margin = 18 - 12 = +6 (Drake)
avg_pace = (68 + 65) / 2 = 66.5
sigma = 11.9 * sqrt(66.5 / 67.5) = 11.81
p_win_Drake = norm.cdf(6 / 11.81) ≈ 69%
```

Indiana State was actually -2.5 betting favorite (~57% implied). Drake won 84-80.

### Neutral Court

All MVC tournament games are played at Enterprise Center in St. Louis — no home court adjustment needed.

---

## Bracket Formats

### Current Format (2015–2026): 12 teams

```
Opening Round (7v10, 8v11, 9v12, 6v?) → Quarterfinals → Semifinals → Final
Seeds 1–6 receive first-round byes to Quarterfinals
Seeds 7–12 play Opening Round
```

### New Format (2027+): 10 teams

```
First Round (3v10, 4v9, 5v8, 6v7) → Semifinals → Final
Seeds 1–2 receive byes to Semifinals
Seeds 3–10 play First Round
```

The key difference: in the new format, the top 2 seeds play fewer games and only need to win 2 games instead of 3. Seeds 3–6 lose their bye and must play an extra game.

---

## Simulation

### Algorithm

For each year:
1. Load team AdjEM and AdjT from `trank_mvc.csv`
2. Load seeds and bracket structure for that year
3. Repeat 10,000 times:
   - Simulate each game using `win_prob()` — draw random uniform, compare to p_win
   - Advance winner, repeat until champion determined
4. Record win count per team
5. Output: championship probability = wins / 10,000

### Outputs

Per year:
- Championship probability per team
- Actual champion (for validation)
- Whether the model's top pick matched the actual champion

Across years:
- Model accuracy (did the highest-probability team win?)
- Calibration: did teams with 70% sim probability actually win ~70% of the time?

### Format Comparison

Run each historical year through both the old (12-team) and new (10-team) bracket to see:
- Does the expected champion change?
- Which seeds benefit most from the new format?

---

## Validation

### Against Actual Results

Compare simulated championship % against actual outcomes (2015–2025). A well-calibrated model should show:
- The actual champion was the model's top pick more often than chance
- Teams with high sim % win the tournament more often than teams with low sim %

### Against Betting Odds

Where odds exist (2022 final: Loyola -5; 2024 final: ISU -2.5 / -160), compare:
- Model implied probability vs betting implied probability (de-vigged)
- Gaps are interesting — either the model is miscalibrated or the market had information not in season stats

### Calibration Check

Group games into probability buckets (50–60%, 60–70%, 70–80%, 80%+) and check if actual win rates match. If not, adjust sigma.

---

## Open Questions

- **Seeds 2015–2022**: Need to fill in or scrape from sports-reference.com
- **Full bracket 2015–2019**: First/second round results not yet collected
- **Sigma calibration**: 11.9 is the standard value but could be recalibrated on MVC-specific data
- **Upset weighting**: Should we model that lower seeds systematically outperform efficiency metrics in tournaments? (Bradley 2019: 5-seed won as 18-point deficit comeback)
