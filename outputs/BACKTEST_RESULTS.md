# DeathOvers IQ: first held-out backtest

Train on 2008–2021; tune on 2022; refit on 2008–2022; test on 2023–2024.
Training stays frozen for both test seasons. No test-based retuning.

Selected strengths: profile=120, run matchup=60, wicket matchup=240. Wicket value 20 is not tuned or validated.

Eligible test groups: 224; common-history groups: 119 (53.1%).
Each group is batter–bowler–phase–season with at least 12 legal test deliveries. Common history means at least one training matchup ball.

## Fair comparison on the same common-history groups

| Method | MAE (bat runs / legal ball) | Ball-weighted MAE | Wicket Brier |
|---|---:|---:|---:|
| League | 0.3928 | 0.3868 | 0.01711 |
| Bowler | 0.4064 | 0.3990 | 0.01718 |
| Raw H2H | 0.5591 | 0.5585 | 0.02532 |
| Shrinkage | 0.3894 | 0.3834 | 0.01707 |

Positive changes below mean lower MAE; negative changes mean worse MAE.
- MAE reduction versus League: +0.87%.
- MAE reduction versus Bowler: +4.19%.
- MAE reduction versus Raw H2H: +30.35%.

## Phase results on common-history groups

| Phase | Groups | Bowler MAE | Raw H2H MAE | Shrinkage MAE |
|---|---:|---:|---:|---:|
| Powerplay | 48 | 0.4760 | 0.6184 | 0.4538 |
| Middle | 67 | 0.3297 | 0.4478 | 0.3217 |
| Death | 4 | 0.8575 | 1.7138 | 0.7509 |

## Including matchups without training head-to-head history

| Method | All-eligible MAE |
|---|---:|
| League | 0.4120 |
| Bowler | 0.4185 |
| Shrinkage | 0.4072 |

Raw H2H has no prediction without direct training history, so it is excluded from this second table.

## How to read this

Lower MAE means the predicted average bat-run rate was closer to the observed test rate. MAE 0.30 means an average absolute rate error of 0.30 bat runs per legal ball, not 30% error. Multiplying by six expresses rate error per six legal deliveries; it is not a single-over forecasting test.

Wicket Brier evaluates event probabilities; a lower value is better. It does not establish calibration. The main run metric gives every eligible matchup group equal weight; the weighted version gives more weight to groups with more test deliveries.

## Limits

- This is one chronological holdout with no statistical significance or confidence-interval claim.
- Groups with fewer than the minimum test balls are excluded. Results may not generalize to them.
- Older player experience is pooled equally with recent seasons; this does not measure current form.
- The target excludes extras and illegal deliveries. Bowler baseline is bat runs conceded on legal balls, not official economy.
- Pitch, venue, toss, handedness and team context are omitted. Recommendations are not causally validated.
- The wicket-value ranking rule and match-win impact are not tested by run-rate MAE.
- Settings selected at the edge of the predefined grid are a limitation; do not expand the grid using test results.
- Profiles overlap with direct history, so the model is a shrinkage heuristic, not an independent-prior posterior.
