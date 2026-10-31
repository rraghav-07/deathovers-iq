# DeathOvers IQ

### Historical IPL matchup analysis for captains and analysts

**[Live Dashboard](https://deathovers-iq.streamlit.app/)** · **[GitHub Repository](https://github.com/rraghav-07/deathovers-iq)**

Choosing a bowler against a particular batter is difficult when their direct matchup history contains only a handful of deliveries.

DeathOvers IQ combines phase-specific player profiles with direct head-to-head history using shrinkage. It lets users compare bowling options, inspect sample sizes and explore the evidence behind each estimate across Powerplay, Middle and Death overs.

## Key findings

- On **119 held-out matchup–phase–season groups**, shrinkage reduced run-rate MAE by **30.35% versus raw head-to-head** and **4.19% versus the bowler baseline**.
- Improvement over the **league phase average was only 0.87%**. The model performed approximately on par with this simple baseline; its strongest measured benefit was stabilising raw head-to-head estimates.
- Only **four death-phase groups** qualified for the common-history comparison. Death-specific predictive strength is not established, and death-over recommendations remain exploratory.

These are results from one chronological holdout, without a statistical-significance claim.

## Explore the dashboard

### Captain’s Cheat Sheet

Select a batter, phase and available bowlers to compare:

- Predicted bat runs per legal delivery.
- Predicted bowler-credited wicket probability per legal delivery.
- Direct head-to-head sample size and its contribution to the estimate.
- A ranking controlled by the chosen wicket-value assumption.
- A runs-versus-wickets chart and downloadable comparison table.

### Batter Profile

Explore phase records and direct matchup history, with sample sizes alongside performance measures.

### Bowler Profile

Inspect phase performance, wickets, descriptive economy and opponent records.

### Model Validation

Compare the model with simple baselines, inspect the chronological evaluation split and review sample limitations.

## Data and database design

The supplied dataset covers **IPL 2008–2024**:

| Item | Count |
|---|---:|
| Matches | 1,095 |
| Recorded deliveries | 260,920 |
| Player names | 732 |
| Super Over deliveries excluded from standard profiles | 161 |
| Standard-innings legal deliveries | 251,319 |

SQLite links delivery facts to match, player and phase information. Season-specific aggregates support player profiles, matchup summaries and chronological evaluation.

### Cricket-specific handling

- Dataset overs `0–5`: Powerplay.
- Dataset overs `6–14`: Middle.
- Dataset overs `15–19`: Death.
- Wides and no-balls are marked as illegal deliveries.
- Run-outs are excluded from bowler-credited wickets.
- Byes and leg-byes are excluded from runs charged to the bowler.
- Super Over records are preserved but excluded from standard profiles.

The model predicts **bat runs and bowler wickets on legal deliveries**. Its run-rate target excludes extras and is different from official bowling economy.

## How the model works

1. Build phase-specific batter and bowler profiles from the training period.
2. Regularise sparse player profiles towards the league phase average.
3. Combine the player profiles into a matchup estimate.
4. Blend that estimate with direct head-to-head history.

The direct-history weight is:

`weight = historical matchup balls / (historical matchup balls + strength)`

Smaller samples receive less weight. Run and wicket estimates use separately selected strengths.

Validation selected:

| Setting | Strength |
|---|---:|
| Player profile | 120 |
| Run matchup | 60 |
| Wicket matchup | 240 |

The ranking score is:

`score = predicted bat runs per legal ball − wicket value × predicted wicket probability`

**Lower scores rank first.** Wicket value is a user-selected assumption, not a learned or validated measure of match impact.

Sample-support labels describe the amount of historical evidence. They are **not calibrated predictive confidence**.

## Held-out evaluation

| Stage | Seasons |
|---|---|
| Initial training | 2008–2021 |
| Parameter selection | 2022 |
| Refit with selected settings | 2008–2022 |
| Final testing | 2023–2024 |

Training remains frozen for both test seasons. Test results were not used to retune settings.

Each eligible test group represents one batter–bowler–phase–season combination with at least **12 legal test deliveries**.

### Common-history comparison

All methods below are evaluated on the **same 119 groups**, each with at least one direct matchup ball in training.

| Method | MAE ↓ | Ball-weighted MAE ↓ | Wicket Brier ↓ |
|---|---:|---:|---:|
| League phase average | 0.3928 | 0.3868 | 0.01711 |
| Bowler phase average | 0.4064 | 0.3990 | 0.01718 |
| Raw head-to-head | 0.5591 | 0.5585 | 0.02532 |
| Shrinkage | **0.3894** | **0.3834** | **0.01707** |

MAE measures absolute error in the average bat-run rate per legal delivery. **MAE 0.3894 does not mean 38.94% error.**

The main MAE gives each eligible group equal weight. Ball-weighted MAE gives more weight to groups containing more test deliveries. Lower wicket Brier scores indicate better probability predictions, but do not establish calibration.

### Results by phase

| Phase | Groups | Bowler MAE | Raw H2H MAE | Shrinkage MAE |
|---|---:|---:|---:|---:|
| Powerplay | 48 | 0.4760 | 0.6184 | 0.4538 |
| Middle | 67 | 0.3297 | 0.4478 | 0.3217 |
| Death | 4 | 0.8575 | 1.7138 | 0.7509 |

The death-phase comparison is too small to support a broad performance claim.

### Including matchups without prior direct history

Across all **224 eligible test groups**:

| Method | MAE ↓ |
|---|---:|
| League phase average | 0.4120 |
| Bowler phase average | 0.4185 |
| Shrinkage | **0.4072** |

Raw head-to-head cannot predict unseen matchups without a fallback, so it is excluded from this table.

## Run locally

Use **Python 3.12** with the pinned dependencies.

```bash
git clone https://github.com/rraghav-07/deathovers-iq.git
cd deathovers-iq
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

### macOS or Linux

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app/streamlit_app.py
```

Open the local URL displayed in the terminal.

The repository includes `data/deathovers.sqlite`, so raw CSVs are not required to explore the dashboard.

## Reproduce the analysis

Run these commands using the project’s virtual-environment Python:

```bash
python model/backtest.py
python model/matchup.py --config outputs/model_config.json
python -m unittest discover -s tests -v
```

To rebuild the database, place the original `matches.csv` and `deliveries.csv` files in `data/raw/`, then run:

```bash
python etl/load_data.py
```

Raw CSVs are not included in the repository. Database-rebuild tests require those source files.

## Project structure

```text
app/             Streamlit dashboard
data/            SQLite database
docs/            Model and evaluation documentation
etl/             CSV cleaning and database loader
model/           Matchup estimates and backtesting
outputs/         Configuration, audit and evaluation results
sql/             Schema and aggregate queries
tests/           Data, model and dashboard checks
.streamlit/      Dashboard theme configuration
requirements.txt Pinned Python dependencies
```

## Limitations

- One chronological holdout does not establish statistical significance or general performance across other periods.
- Groups with fewer than 12 legal test deliveries are excluded from evaluation.
- Only four death-phase groups qualify for the common-history comparison.
- Historical seasons are pooled without recency weighting; estimates do not measure current form.
- Pitch, venue, toss, handedness, team context and current squad availability are omitted.
- The prediction target excludes extras and illegal deliveries.
- Wicket-value rankings and match-winning impact have not been validated.
- Some selected strengths lie at the edge of the predefined tuning grid.
- Player profiles overlap with direct matchup history. This is a shrinkage heuristic, not an independent-prior Bayesian posterior.

## Technology

Python · pandas · NumPy · SQLite · Streamlit · Plotly

## Data attribution

The project uses user-supplied IPL match and ball-by-ball CSVs covering 2008–2024.

**Attribution is incomplete:** the exact original Kaggle dataset URL, creator, version and dataset licence still need to be recorded. The included SQLite database is derived from these files and remains subject to the source dataset’s applicable terms.

## Code licence

A code licence has not yet been added. The dataset’s licence is separate from any licence subsequently applied to the application code.
