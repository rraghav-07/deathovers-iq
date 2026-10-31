# DeathOvers IQ — dashboard version

## Open the project

Extract the complete ZIP. Open its included **deathovers-iq** folder in VS Code.
Choose **Terminal > New Terminal**. Your current folder should contain `app`,
`model`, `data`, `sql` and `requirements.txt`.

## Install and start

Run these two commands, one at a time:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app/streamlit_app.py
```

Streamlit normally opens a browser. If it does not, visit:

http://localhost:8501

Leave the terminal running while using the dashboard. Press Ctrl+C to stop.
You only need the installation command the first time. Use `py -m streamlit`,
not `py app/streamlit_app.py` and not `cd app` followed by the same path.

The database, fitted settings and backtest outputs are included. You do not
need to rebuild or rerun the backtest to open the dashboard.

## Try the four pages

| Page | Try this | What it means |
|---|---|---|
| Captain's Cheat Sheet | Keep V Kohli, Death and the four default bowlers | Compare estimates among your selected bowlers |
| Captain's Cheat Sheet | Move wicket value from 20 to 0 | Zero ranks by predicted batting runs alone |
| Batter Profile | Inspect Kohli's phase rates and change the direct-history threshold | See phase strengths and how few balls some records contain |
| Bowler Profile | Inspect JJ Bumrah's economy and wicket rates | See past performance by phase |
| Model Validation | Switch between common-history and all eligible groups | Understand the fair baseline comparison and missing-history coverage |

Recommendations and profile records use history through **2022**. The dataset
also contains 2023–2024, reserved for the frozen backtest. This is a historical
demo, not current IPL squad advice or a live match service.

## Read the estimates

- Bat runs / legal ball excludes extras and illegal-delivery outcomes.
- Wicket probability refers to a bowler-credited wicket on a legal delivery.
- The score combines the two with an assumed wicket value; lower ranks first.
- Support labels describe direct sample counts, not calibrated confidence.
- Run and wicket estimates have different direct-history weights because their
  validation-selected strengths are 60 and 240 respectively.
- Official economy in the bowler profile includes runs charged from wides and
  no-balls. It is a descriptive profile metric, not the model's prediction target.
- The batter profile uses bat runs per 100 legal balls, explicitly not official
  strike rate. Run-outs are not included in its bowler-wicket rate.

## First measured finding

On 119 common-history held-out matchup-phase-season groups, shrinkage reduced
run-rate MAE by 4.19% against the bowler baseline and 30.35% against raw H2H.
It improved on the league phase baseline by only 0.87%. Only four common-history
death-phase groups qualified; no strong death-specific claim is supported.

## Verification and reproducibility

```powershell
py -m unittest discover -s tests -v
py etl/load_data.py
py model/backtest.py
```

The first command tests database rules, connection lifecycle, model maths,
season separation, backtest calculations and dashboard interactions. The
remaining commands reproduce the database and results if needed. Stop the
dashboard before rebuilding its database, particularly on Windows.

See `README.md`, `docs/STEP2_MODEL.md` and `docs/STEP3_BACKTEST.md` for details.

## Remaining work

The local dashboard is complete. Public GitHub, hosting and a Devpost submission
have not been created. Record the exact source dataset URL and licence before
publishing data; the CSVs and generated database are Git-ignored by default.
