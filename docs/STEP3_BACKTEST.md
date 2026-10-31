# Step 3: test predictions on unseen seasons

## Run this version

This complete ZIP contains a `deathovers-iq` folder, including the source CSVs
and built database. Extract it and open that included folder in VS Code.
Choose Terminal > New Terminal. Confirm that `data`, `model` and `etl` are
inside the current folder, then run:

```powershell
py model/backtest.py
```

No pip installation is needed. This produces the validation grid, frozen
configuration, holdout predictions and results in `outputs`.

To see a recommendation with the validation-selected configuration:

```powershell
py model/matchup.py --config outputs/model_config.json
```

The previous `py model/matchup.py` command intentionally retains the original
provisional settings and 2021 cutoff. Using `--config` selects the tuned
strengths and the 2022 training cutoff. Changing the data cutoff changes
estimates; rankings need not match the earlier demonstration.

## What we did

1. Fit initial profiles using 2008–2021 only.
2. Use eligible 2022 matchup-phase groups to select run-profile and run-matchup
   shrinkage strengths from a fixed grid. Minimize equal-weight group MAE.
3. Holding that profile strength fixed, select wicket-matchup strength by
   per-delivery Brier score on the same 2022 validation groups.
4. Save the selected settings before accessing the test groups.
5. Refit player and matchup histories through 2022.
6. Predict eligible 2023 and 2024 groups without updating history during either
   season. Compare predictions with actual legal-ball bat-run rates.

An evaluation group is **one batter, bowler, phase and season** with at least
12 legal test deliveries. The thresholds, candidate grid and evaluation unit
are fixed in code; they were not changed after seeing the holdout results.

## Why compare on the same groups?

Raw head-to-head has no forecast if the players never met in that phase in
training. The primary table therefore compares every method on the same
119 groups with prior history. There are 224 eligible groups overall; the
second table includes all of them, comparing methods that can predict unseen
matchups. It would be unfair to give each method a different test subset and
compare those error scores directly.

## What MAE means

If the actual test rate is 1.5 bat runs per legal ball and the estimate is 1.2,
the absolute error is 0.3. MAE averages those errors over groups. Lower is
better. A 4.19% MAE reduction does not mean 95.81% accuracy, nor does it mean
4.19% fewer runs will be conceded when a captain follows the recommendation.

The bowler baseline is the bowler's historical bat-run rate in that phase on
legal deliveries. It is not official economy. All methods predict the same
target, which excludes extras and illegal deliveries.

## Interpreting this first result

On the 119 common-history test groups, shrinkage MAE is about 0.3894 versus
0.4064 for the bowler baseline and 0.5591 for raw H2H. That is a 4.19% and
30.35% reduction respectively. The league phase baseline is 0.3928, only
0.87% worse than shrinkage: the extra predictive value is modest.

Only four death-phase groups qualify for that primary comparison. Do not
advertise the result as strong evidence for death-over recommendations.
No statistical significance, calibrated confidence, match-win improvement or
causal recommendation benefit has been established.

The selected profile strength (120) and wicket strength (240) are at the
upper grid boundary. Report this as a limitation. Do not expand the grid
based on test outcomes and continue calling those seasons an untouched test.

## Output files

| File | Purpose |
|---|---|
| `BACKTEST_RESULTS.md` | Readable result tables, interpretation and limitations |
| `backtest_results.json` | Exact metrics for the future dashboard |
| `test_predictions.csv` | Every eligible holdout group's actual rate and predictions |
| `validation_grid.csv` | Run-model candidates evaluated on 2022 |
| `validation_wicket_grid.csv` | Wicket candidates evaluated on 2022 |
| `model_config.json` | Frozen settings selected on validation data |

The Streamlit dashboard now displays these measured results alongside the
Captain's Cheat Sheet. See `START_HERE.md` to launch it.
