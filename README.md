# DeathOvers IQ — IPL captain's matchup advisor

Start with **START_HERE.md** for the complete local dashboard instructions.

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app/streamlit_app.py
```

Four dashboard pages: Captain's Cheat Sheet, Batter Profile, Bowler Profile
and Model Validation. This is a historical demo using the backtested setup
through 2022, with 2023–2024 held out. It is not a current-form advisor.

An IPL captain's matchup advisor, built in explained stages.

## What works now

The supplied 2008–2024 files are loaded into a SQLite star schema. The package
contains the working database, SQL, reproducible loader, source CSVs and audit.
A provisional matchup model is now available: see `docs/STEP2_MODEL.md` for
instructions and explanations. Run `python model/matchup.py` for an example.
The first chronological backtest is complete: see `docs/STEP3_BACKTEST.md`.
Run `python model/backtest.py` to reproduce it, then
`python model/matchup.py --config outputs/model_config.json` to use the tuned
configuration. Shrinkage reduced MAE by 4.19% versus the bowler baseline and
30.35% versus raw H2H on 119 common-history test groups; the improvement over
the league phase average was only 0.87%. Only four common-history death-phase
groups qualified. The local Streamlit dashboard is complete; public deployment
and repository publication remain to be done.

## Run on Windows

1. Extract this ZIP. Open the extracted `deathovers-iq` folder in File Explorer.
2. Click its address bar, type `powershell`, and press Enter.
3. Check Python: `python --version` (or use `py` in place of `python`).
4. Run `python etl/load_data.py`.
5. Look for `Database ready` and three checks marked `passed`.

No pip packages or SQLite server installation are needed for this stage.
The included database is already built; running the loader safely rebuilds it
from `data/raw/matches.csv` and `data/raw/deliveries.csv`.
Paths are resolved relative to the loader, so moving the project folder is safe.

## What the database means

| Object | Meaning |
|---|---|
| `fact_deliveries` | Every source delivery, linked to match, batter, bowler and phase |
| `dim_player` | Unique names appearing as batter or bowler; not a current squad list |
| `dim_match` | Match date, original season label, calendar season, venue and teams |
| `dim_phase` | Powerplay, Middle and Death |
| `agg_matchup` | Season + batter + bowler + phase totals |
| `agg_batter_phase` | Season + batter + phase totals |
| `agg_bowler_phase` | Season + bowler + phase totals |
| `agg_league_phase` | Season + phase totals for league baselines |
| `ranked_bowler_phase` | Example SQL window function ranking wicket totals per season and phase |

The aggregates are SQL views, not duplicate source files. They always reflect
the fact table. Every aggregate retains season, allowing training-only queries.
Indexes help SQLite find matches and player/phase combinations efficiently.

## Cricket and modelling definitions

- Source over indexes 0–5 map to Powerplay, 6–14 Middle, 15–19 Death.
- All 260,920 deliveries are retained for audit. Standard profiles exclude the
  161 rows from innings above 2 (Super Overs).
- Wides and no-balls are not legal balls. They remain in the fact table.
- `runs` is runs off the bat, including any scored on illegal deliveries.
- `runs_conceded` includes bat runs plus wide/no-ball extras. Byes, leg-byes
  and penalty extras are excluded from bowler charges under the source's
  single extras-type representation.
- `wickets` counts caught, bowled, lbw, stumped, caught-and-bowled and hit wicket.
  Run-outs, retirements and obstructing the field do not earn bowler wickets.
- The first prediction target will be **bat runs per legal delivery**, with
  bowler-credited wicket probability **per legal delivery**. `model_runs` and
  `model_wickets` contain only events on legal deliveries, with `balls` as the
  common denominator. This is not official economy or official batting strike
  rate. In particular, it omits runs and wickets on illegal deliveries.
- Official batting strike rate uses a different balls-faced definition. We
  will label profile metrics explicitly rather than call this target strike rate.
- Original season strings are retained. The calendar year of the match date
  is used for chronological splits: the season labelled `2020/21` is 2020 here.
- Names are trimmed but not automatically merged. Initials and name changes
  may require a documented alias map later.
- This data supports historical analysis through 2024, not live IPL conditions.

## Checks performed

The loader verifies match-key uniqueness, source delivery links, player names,
known extra types, nonnegative runs, run arithmetic, over/innings ranges,
foreign keys, SQLite integrity and aggregate-to-source legal-ball totals.
A failed build does not replace an existing database. Audit counts and source
SHA-256 hashes are written to `outputs/data_quality.json`.
Exact duplicate source rows were also checked during initial inspection: none.
Rows are not deduplicated by over and ball, because repeated ball labels can
occur legitimately after illegal deliveries.

## Planned modelling split

2008–2021: initial training; 2022: hyperparameter validation; 2023–2024:
untouched final test. After tuning on 2022, refit on 2008–2022 before evaluating
the combined 2023–2024 holdout. Use no test-season records for predictions.

## Source and publication

Raw CSVs were supplied by the user in `archivEEEEEE.zip`. The exact Kaggle
dataset URL and redistribution licence have not yet been supplied. Record
them before public release. Raw CSVs and generated databases are ignored by
Git by default; do not publish the bundled data without checking its licence.

## Next stage

Run the local dashboard, then prepare public hosting and repository publication
with source attribution and data licence details.
