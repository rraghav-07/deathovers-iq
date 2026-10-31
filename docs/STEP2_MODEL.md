# Step 2: the matchup model

## Install this update

Extract the update ZIP into your existing `deathovers-iq` folder (the one
containing `data`, `etl` and `sql`). Allow replacement of existing files.
After extraction there should be a `model` folder alongside `etl`.
The update includes the Windows connection-close fix for the loader.
Your existing database and raw CSV files stay in place.

From PowerShell in `deathovers-iq`, run:

```powershell
py model/matchup.py
```

No pip installation is required yet. This runs an example comparing JJ Bumrah,
R Ashwin, RA Jadeja and SP Narine against V Kohli in the death phase, using
only seasons through 2021. Their presence in this example is hypothetical:
the model does not check teams, current squads or overs remaining.

To change the selection:

```powershell
py model/matchup.py --batter "V Kohli" --phase Middle --bowlers "JJ Bumrah" "R Ashwin" "RA Jadeja"
py model/matchup.py --batter "V Kohli" --phase Death --bowlers "JJ Bumrah" "SP Narine" --wicket-value 0
py model/matchup.py --list-players --phase Death
```

Use exact player spellings from the dataset. The list command shows bowlers
with experience in the selected phase before the cutoff, not current squads.
Output details are written to `outputs/example_recommendation.json`.

## What happens inside

1. SQL selects only seasons up to the training cutoff. Default: 2021.
2. Compute the league bat-run rate and bowler-wicket probability per phase.
3. Smooth batter and bowler phase profiles toward the league using a provisional
   60-ball strength. This prevents a very small player sample from dominating.
4. For runs, multiply the smoothed batter and bowler rates, then divide by the
   league rate. This is a multiplicative heuristic, not the binary log5 formula.
5. For wickets, combine batter and bowler event odds relative to league odds:
   `matchup_odds = batter_odds * bowler_odds / league_odds`, then convert odds
   to probability with `odds / (1 + odds)`.
6. Blend each profile prediction with direct history:
   `prediction = (k * profile_prediction + observed_events) / (k + matchup_balls)`.
7. Rank the supplied bowlers by `runs_per_ball - wicket_value * wicket_probability`.
   Lower is preferable under this assumption. The default wicket value is 20.

Example: expected bat-run rate 1.5; observed 20 runs from 10 legal balls;
strength k=30. The estimate is `(30*1.5 + 20)/(30+10) = 1.625`. The direct
matchup contributes 25%, and player profiles contribute 75%.

## Understand the columns

| Column | Meaning |
|---|---|
| Runs/ball | Estimated bat runs on a legal delivery; excludes extras |
| Wicket % | Estimated probability of a bowler-credited wicket on a legal delivery |
| H2H balls | Direct legal deliveries in this phase through the training cutoff |
| H2H weight | Percentage of the run estimate coming from direct history |
| Score | Ranking value under the chosen wicket-value assumption |

There are no formal confidence intervals in this stage. Support labels mean
zero balls, fewer than 30 balls, or at least 30 balls of direct history. They
are descriptive counts, not validated confidence levels. Profile sample sizes
and any league fallback are included in the detailed JSON.

## What the result does and does not establish

This is a working prediction pipeline, not evidence that it beats a baseline.
The 30-ball matchup strength and 60-ball profile strength are provisional.
The next stage tunes settings on 2022 and evaluates the frozen method on
2023–2024. Training-profile rates use all pre-cutoff experience, not a recent
form weighting. We do not call these estimates current form.

Bowler baseline, raw H2H and model predictions in the backtest must use the
same legal-delivery bat-run target. Official economy, which includes wides
and no-balls, is a different target and should not be substituted silently.
Raw H2H predictions are undefined when training H2H balls are zero; the
backtest will report coverage and compare all methods on a shared subset.

Profiles include the pair's direct history as part of each player's experience.
Thus the blend is an empirical prediction heuristic, not an independent-prior
Bayesian posterior. Its usefulness must be assessed empirically.

The score is a preference rule, not a calibrated forecast of match victory.
A negative score is possible and does not mean negative predicted runs.
No pitch, venue, handedness, toss or batting partner adjustment is included.
Choosing a recommended bowler has not been causally validated by this model.

## Verify

```powershell
py -m unittest discover -s tests -v
```

Tests cover hand-calculated shrinkage, bounded wicket probabilities, no-history
fallback, score changes, invalid inputs and protection against future-season
data affecting earlier predictions, plus database and Windows lifecycle checks.
