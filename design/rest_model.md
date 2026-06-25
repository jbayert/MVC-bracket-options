# Rest / Bye Advantage Model

## Goal
Add a rest-aware variant of the win-probability model. Teams that earn byes play
fewer games and get more rest; teams without byes grind out more consecutive
games. The base model (`simulate.py` / `analyze.py`) ignores this entirely.

## Findings (from research)

| Effect | Estimate | Notes |
|--------|----------|-------|
| Rest advantage | **+2.5 pts per extra rest day** | College range 2–3 pts/day; NBA ~3–4 (older players). 2.5 = conservative midpoint. |
| Cumulative fatigue | **−0.75 pts per extra game already played** | Chronic strain across a multi-day tournament, distinct from acute rest. |
| Net bye effect | **+1.5 to +2.5 pts** | Rust is real but only shows in the first few minutes and does **not** reverse the rest edge at realistic bye lengths (3–5 days). |

**Direction is certain (rest helps); the coefficient is not.** Credible range
2.0–3.0 pts/day, best single value 2.5. Validate against our 2015–2025 results
rather than trusting the prior.

> Citation caveat: the numeric ranges match the well-known college-basketball
> consensus (KenPom/Torvik have written 2–3 pts/day), but some specific paper
> titles the research surfaced look unreliable. Treat the numbers as priors, not
> the bibliography as sources.

## Model

Add a rest term to the existing neutral-court margin:

```
rest_adj   = REST_COEFF    * (rest_days_A   - rest_days_B)     # REST_COEFF = 2.5
fatigue    = FATIGUE_COEFF * (games_played_A - games_played_B) # FATIGUE_COEFF = 0.75
margin     = (AdjEM_A - AdjEM_B) + rest_adj - fatigue
p_win      = norm.cdf(margin / sigma)
```

`rest_days` and `games_played` are *correlated* but not redundant: rest_days is
the acute gap since the last game (captures the bye), games_played is chronic
load (captures a team on its 3rd game in 4 days). Keeping both is defensible;
they are separate knobs so either can be zeroed when tuning.

### Schedule assumptions (4-day MVC tournament, one round per day)

| Format | Day 1 | Day 2 | Day 3 | Day 4 |
|--------|-------|-------|-------|-------|
| 10-team double bye | R1 (seeds 3–10) | QF | SF (seeds 1–2 enter) | Final |
| 8-team no byes | R1 (all 8) | SF | Final | — |
| 10-team six byes | Opening (7–10) | QF (seeds 1–6 enter) | SF | Final |

- A team's `rest_days` for a game = days since its previous game.
- A team entering fresh (first appearance / bye) is treated as well-rested but
  **capped at `REST_CAP = 3`** so a long pre-tournament layoff doesn't run away
  (this is where rust would otherwise be ignored).
- `games_played` starts at 0 and increments each game won.

### Expected impact
Seeds 1–2 championship % rises (their bye is now rewarded), seeds 3–6 fall (they
pay for the extra game + short rest). The double-bye format should show the
largest swing, since the bye skips two rounds.

## Implementation
- `simulate_rest.py` — tree-based bracket sim that threads `(team, games_played,
  last_day)` through each game so rest/fatigue can be computed per matchup.
  Reuses the same `win_prob` core plus the rest term. Runs every year × format
  **with and without** the rest adjustment and reports the accuracy delta.
- Coefficients (`REST_COEFF`, `FATIGUE_COEFF`, `REST_CAP`) are module constants.
