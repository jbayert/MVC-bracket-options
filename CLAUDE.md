# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Models for the Missouri Valley Conference basketball tournament ("Arch Madness"). The MVC announced (June 2026) a format change from 12 teams to 10 teams with semifinal byes for the top 2 seeds, effective 2027. This repo simulates historical tournaments (2015–2025, skipping the cancelled 2020) under different bracket formats to see how the format affects who wins.

## Pipeline

The scripts form a strict dependency chain — run them in order after changing upstream data:

```
T-rank data/*.htm  --parse_trank.py-->  data/trank_mvc.csv
data/trank_mvc.csv + data/arch_madness_seeds.csv + data/arch_madness_champions.csv
                   --analyze.py-->  data/simulations_raw.csv, simulation_summary.csv, analysis_by_year.csv
                   --make_brackets.py-->  site/brackets/*.svg
                   --build_site.py-->  site/index.html
```

Commands (pure Python 3 stdlib, no dependencies, no venv):
- `python parse_trank.py` — parse saved barttorvik HTML into `data/trank_mvc.csv`
- `python simulate.py [year] [--sims N]` — print one year's sim across all 3 formats (exploratory; writes nothing)
- `python analyze.py [--sims N]` — run all years × all formats, write the 3 simulation CSVs (default 10,000 sims)
- `python make_brackets.py && python build_site.py` — regenerate the website
- Open the site: `start "" "site\index.html"` (Windows). Charts need internet (Chart.js CDN).

There are no tests and no build/lint tooling. Scripts that contain non-trivial logic carry an inline `assert` self-check (e.g. `make_brackets.py`).

## Core model (the part that needs reading multiple files)

Win probability for a single neutral-court game is computed identically in `simulate.py` and `analyze.py` (`win_prob` / `sim_game`):

```
expected_margin = AdjEM_A - AdjEM_B          # AdjEM = adj_oe - adj_de, from T-Rank
sigma = 11.9 * sqrt(avg_pace / 67.5)         # avg_pace = mean of the two adj_t
p_win = normal_cdf(expected_margin / sigma)
```

`sigma=11.9` is the KenPom-calibrated SD of college basketball outcomes; tempo scales it. All tournament games are neutral-court (no home adjustment). `DESIGN.md` documents the rationale.

The win-prob/bracket logic is **duplicated** between `simulate.py` (single-year, prints a table) and `analyze.py` (all years, writes CSVs). If you change the model or a bracket shape, change both. The three bracket functions encode the formats:
- `bracket_10_double_bye` — new 2027 format: seeds 1–2 bye to semis
- `bracket_8_no_byes` — top 8 seeds, straight bracket
- `bracket_10_six_byes` — current-style: seeds 1–6 bye to quarterfinals

## Data conventions

- **Seeds**: the `seed` column in `data/trank_mvc.csv` is the *NCAA* tournament seed and is mostly blank — do not use it for MVC seeding. The authoritative MVC tournament seeds are in `data/arch_madness_seeds.csv`. `analyze.py` joins them by team name.
- **Team name matching**: T-Rank uses abbreviated names ("Illinois St.", "UIC") while seed/champion data uses full names ("Illinois State", "Illinois Chicago"). Both `analyze.py` and `simulate.py` carry an `ALIASES`/`_name_match` map to reconcile these. Add new teams there. Unmatched teams fall back to AdjEM-rank seeding.
- **Years**: `YEARS = [2015..2025]` excludes 2020 everywhere. The T-rank HTML for 2020 and 2026 exists but is skipped by the simulation year list.
- `data/README.md` tracks per-file completeness; bracket results and betting odds are only partial.

## Site

`site/index.html` is generated — never hand-edit it; edit `build_site.py` and rerun. All CSV data is embedded as a single inline `DATA` JSON object so the page runs from `file://`. JSON object keys are year strings (`DATA.teams["2025"]`), which JS bracket-access with an integer year resolves fine.
