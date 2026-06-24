# Arch Madness Data

Missouri Valley Conference tournament data for prediction modeling.

## Files

| File | Contents | Completeness |
|------|----------|--------------|
| `arch_madness_champions.csv` | Champion + runner-up + final score per year | Complete 2015-2025 (skip 2020) |
| `arch_madness_bracket_results.csv` | Game-by-game results by round | Complete 2021-2025; 2015-2019 missing |
| `arch_madness_seeds.csv` | Team seeds per year | Complete 2023-2025; 2015-2022 missing |
| `arch_madness_format.csv` | Bracket format by era | Complete |

## Still Needed

- **T-Rank stats** (AdjO, AdjD, AdjEM, AdjT) per team per year — barttorvik.com blocks HTTP, needs Playwright scraper or `cbbpy` package
- **Seeds 2015-2022** — needs sports-reference.com scrape
- **Full bracket results 2015-2019** — needs sports-reference.com scrape
- **Betting odds** — OddsPortal/Covers; reliable 2022+, spotty 2018-2021, gaps pre-2018

## Win Probability Method (planned)

KenPom-style efficiency margin approach:
- `expected_margin = AdjEM_A - AdjEM_B` (neutral court)
- `p_win = norm.cdf(expected_margin / sigma)` where sigma adjusts for combined tempo
- Betting odds (moneyline de-vigged) as validation column where available

## Format Change (2027)

MVC announced June 22, 2026: tournament shrinks from 12 to 10 teams.
Top 2 seeds get semifinal byes instead of top 6 getting quarterfinal byes.
Simulation goal: run historical years through both formats to compare expected champions.
