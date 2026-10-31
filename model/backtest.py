"""Tune on 2022, freeze settings, then evaluate a 2023–2024 holdout."""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.matchup import MatchupModel, PHASES, Totals

# Fixed before looking at holdout results. Do not expand this grid based on them.
PROFILE_GRID = (30.0,60.0,120.0)
MATCHUP_GRID = (5.0,15.0,30.0,60.0,120.0,240.0)
RUN_METHODS = ('League','Bowler','Raw H2H','Shrinkage')

def observed_groups(db,seasons,min_balls=12):
    if not seasons or min_balls<1:
        raise ValueError('Provide seasons and a positive minimum ball count.')
    with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as con:
        keys=','.join('?' for _ in seasons)
        rows=con.execute(f'''SELECT season,batter_key,bowler_key,phase_key,
            SUM(balls),SUM(model_runs),SUM(model_wickets)
            FROM agg_matchup WHERE season IN ({keys})
            GROUP BY season,batter_key,bowler_key,phase_key HAVING SUM(balls)>=?
            ORDER BY season,batter_key,bowler_key,phase_key''',(*seasons,min_balls)).fetchall()
    if not rows:
        raise ValueError('No eligible evaluation matchups; check seasons and minimum balls.')
    return [dict(zip(('season','batter_key','bowler_key','phase_key','balls','runs','wickets'),r)) for r in rows]

def predict_groups(model,groups):
    phases={v:k for k,v in PHASES.items()}
    output=[]
    for g in groups:
        if g['season']<=model.through_season:
            raise ValueError('Evaluation seasons must be strictly later than the training cutoff.')
        batter,bowler=model.names_by_key[g['batter_key']],model.names_by_key[g['bowler_key']]
        ph=g['phase_key']
        p=model.predict(batter,bowler,phases[ph])
        league=model.league[ph]
        bt=model.bowlers.get((g['bowler_key'],ph),Totals())
        output.append(dict(**g,batter=batter,bowler=bowler,phase=phases[ph],
            actual_runs=g['runs']/g['balls'],
            run_predictions={'League':league.runs/league.balls,
                'Bowler':p['bowler_baseline_runs_per_ball'],
                'Raw H2H':p['raw_h2h_runs_per_ball'],
                'Shrinkage':p['expected_runs_per_legal_ball']},
            wicket_predictions={'League':league.wickets/league.balls,
                'Bowler':bt.wickets/bt.balls if bt.balls else league.wickets/league.balls,
                'Raw H2H':p['raw_h2h_wicket_probability'],
                'Shrinkage':p['wicket_probability_per_legal_ball']},
            training_matchup_balls=p['matchup_balls'],
            profile_fallback=p['profile_fallback'],bowler_fallback=bt.balls==0))
    return output

def metrics(rows,method):
    if not rows:
        return None
    if any(r['run_predictions'][method] is None for r in rows):
        raise ValueError('Undefined predictions: use the common-history subset for raw H2H.')
    balls=sum(r['balls'] for r in rows)
    errors=[abs(r['run_predictions'][method]-r['actual_runs']) for r in rows]
    # Exactly the per-delivery Bernoulli Brier score, using grouped event counts.
    brier=sum(r['balls']*r['wicket_predictions'][method]**2
              -2*r['wicket_predictions'][method]*r['wickets']+r['wickets'] for r in rows)/balls
    return dict(groups=len(rows),balls=balls,mae=sum(errors)/len(rows),
        ball_weighted_mae=sum(e*r['balls'] for e,r in zip(errors,rows))/balls,
        wicket_brier=brier)

def comparison(rows,common=True):
    selected=[r for r in rows if r['training_matchup_balls']>0] if common else rows
    methods=RUN_METHODS if common else ('League','Bowler','Shrinkage')
    return dict(groups=len(selected),balls=sum(r['balls'] for r in selected),
                methods={m:metrics(selected,m) for m in methods})

def relative_improvement(baseline,model):
    return 100*(baseline-model)/baseline if baseline else None

def write_csv(path,rows):
    if not rows:
        return
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def run(db,min_balls=12,out=ROOT/'outputs'):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    validation=observed_groups(db,(2022,),min_balls)
    trials=[]
    print(f'Validation: {len(validation)} matchup-phase-season groups in 2022.',flush=True)
    best=None
    for strength in PROFILE_GRID:
        model=MatchupModel(db,2021,profile_strength=strength)
        for k in MATCHUP_GRID:
            model.k_runs=k
            result=metrics(predict_groups(model,validation),'Shrinkage')
            trial=dict(profile_strength=strength,k_runs=k,validation_mae=result['mae'])
            trials.append(trial)
            key=(result['mae'],strength,k)
            if best is None or key<best[0]:
                best=(key,trial)
        print(f'Checked profile strength {strength:g}.',flush=True)
    selected=best[1]
    model=MatchupModel(db,2021,k_runs=selected['k_runs'],profile_strength=selected['profile_strength'])
    wicket_trials=[]
    for k in MATCHUP_GRID:
        model.k_wickets=k
        result=metrics(predict_groups(model,validation),'Shrinkage')
        wicket_trials.append(dict(k_wickets=k,validation_brier=result['wicket_brier']))
    chosen_wicket=min(wicket_trials,key=lambda r:(r['validation_brier'],r['k_wickets']))
    config=dict(through_season=2022,k_runs=selected['k_runs'],
        k_wickets=chosen_wicket['k_wickets'],profile_strength=selected['profile_strength'],
        tuned_on=2022,test_seasons=[2023,2024],min_test_balls=min_balls,
        status='Validation-selected; holdout evaluated without retuning')
    # Persist settings BEFORE evaluating the test seasons.
    (out/'model_config.json').write_text(json.dumps(config,indent=2)+'\n')
    write_csv(out/'validation_grid.csv',trials)
    write_csv(out/'validation_wicket_grid.csv',wicket_trials)
    model=MatchupModel(db,2022,config['k_runs'],config['k_wickets'],config['profile_strength'])
    holdout=predict_groups(model,observed_groups(db,(2023,2024),min_balls))
    report=dict(config=config,protocol=dict(initial_training='2008–2021',validation='2022',
        final_training='2008–2022',holdout='2023–2024; frozen training cutoff for both seasons',
        unit='One batter–bowler–phase–season group with at least N test legal balls',
        target='Bat runs per legal delivery; excludes extras',
        primary_metric='Equal-weight group MAE on common-history groups',
        tuning_objective='Equal-weight group MAE on all eligible 2022 groups',
        wicket_metric='Per-legal-delivery Brier score; lower is better',
        min_test_balls=min_balls,raw_h2h_min_training_balls=1,
        note='Held-out groups are selected by exposure, not outcomes. No history update within test.'),
        validation=dict(groups=len(validation),run_grid=trials,wicket_grid=wicket_trials),
        eligible_test_groups=len(holdout),
        common_history=comparison(holdout),all_eligible=comparison(holdout,False),
        by_phase={ph:comparison([r for r in holdout if r['phase']==ph]) for ph in PHASES},
        by_season={str(s):comparison([r for r in holdout if r['season']==s]) for s in (2023,2024)},
        profile_fallback_groups=sum(r['profile_fallback'] for r in holdout),
        bowler_fallback_groups=sum(r['bowler_fallback'] for r in holdout))
    (out/'backtest_results.json').write_text(json.dumps(report,indent=2)+'\n')
    flat=[]
    for r in holdout:
        record={k:v for k,v in r.items() if k not in ('run_predictions','wicket_predictions')}
        record.update({f'runs_{m}':v for m,v in r['run_predictions'].items()})
        record.update({f'wickets_{m}':v for m,v in r['wicket_predictions'].items()})
        flat.append(record)
    write_csv(out/'test_predictions.csv',flat)
    text=render_report(report)
    (out/'BACKTEST_RESULTS.md').write_text(text,encoding='utf-8')
    print(text)
    print(f'Artifacts saved in {out.resolve()}')
    return report

def render_report(report):
    c=report['config']
    common=report['common_history']
    lines=['# DeathOvers IQ: first held-out backtest','',
        'Train on 2008–2021; tune on 2022; refit on 2008–2022; test on 2023–2024.',
        'Training stays frozen for both test seasons. No test-based retuning.', '',
        f'Selected strengths: profile={c["profile_strength"]:g}, run matchup={c["k_runs"]:g}, '
        f'wicket matchup={c["k_wickets"]:g}. Wicket value 20 is not tuned or validated.', '',
        f'Eligible test groups: {report["eligible_test_groups"]}; common-history groups: '
        f'{common["groups"]} ({common["groups"]/report["eligible_test_groups"]:.1%}).',
        'Each group is batter–bowler–phase–season with at least '
        f'{c["min_test_balls"]} legal test deliveries. Common history means at least one training matchup ball.', '',
        '## Fair comparison on the same common-history groups','',
        '| Method | MAE (bat runs / legal ball) | Ball-weighted MAE | Wicket Brier |',
        '|---|---:|---:|---:|']
    for method,result in common['methods'].items():
        if result:
            lines.append(f'| {method} | {result["mae"]:.4f} | {result["ball_weighted_mae"]:.4f} | {result["wicket_brier"]:.5f} |')
    if common['groups']:
        model=common['methods']['Shrinkage']['mae']
        lines+=['','Positive changes below mean lower MAE; negative changes mean worse MAE.']
        for baseline in ('League','Bowler','Raw H2H'):
            base=common['methods'][baseline]['mae']
            change=relative_improvement(base,model)
            lines.append(f'- MAE reduction versus {baseline}: {change:+.2f}%.' if change is not None else f'- {baseline}: undefined relative change (zero MAE).')
    lines+=['','## Phase results on common-history groups','',
        '| Phase | Groups | Bowler MAE | Raw H2H MAE | Shrinkage MAE |','|---|---:|---:|---:|---:|']
    for phase,result in report['by_phase'].items():
        m=result['methods']
        if result['groups']:
            lines.append(f'| {phase} | {result["groups"]} | {m["Bowler"]["mae"]:.4f} | {m["Raw H2H"]["mae"]:.4f} | {m["Shrinkage"]["mae"]:.4f} |')
    lines+=['','## Including matchups without training head-to-head history','',
        '| Method | All-eligible MAE |','|---|---:|']
    for method,result in report['all_eligible']['methods'].items():
        lines.append(f'| {method} | {result["mae"]:.4f} |')
    lines+=['','Raw H2H has no prediction without direct training history, so it is excluded from this second table.', '',
        '## How to read this','',
        'Lower MAE means the predicted average bat-run rate was closer to the observed test rate. '
        'MAE 0.30 means an average absolute rate error of 0.30 bat runs per legal ball, not 30% error. '
        'Multiplying by six expresses rate error per six legal deliveries; it is not a single-over forecasting test.', '',
        'Wicket Brier evaluates event probabilities; a lower value is better. It does not establish calibration. '
        'The main run metric gives every eligible matchup group equal weight; the weighted version gives more '
        'weight to groups with more test deliveries.', '',
        '## Limits','',
        '- This is one chronological holdout with no statistical significance or confidence-interval claim.',
        '- Groups with fewer than the minimum test balls are excluded. Results may not generalize to them.',
        '- Older player experience is pooled equally with recent seasons; this does not measure current form.',
        '- The target excludes extras and illegal deliveries. Bowler baseline is bat runs conceded on legal balls, not official economy.',
        '- Pitch, venue, toss, handedness and team context are omitted. Recommendations are not causally validated.',
        '- The wicket-value ranking rule and match-win impact are not tested by run-rate MAE.',
        '- Settings selected at the edge of the predefined grid are a limitation; do not expand the grid using test results.',
        '- Profiles overlap with direct history, so the model is a shrinkage heuristic, not an independent-prior posterior.', '']
    return '\n'.join(lines)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'data/deathovers.sqlite')
    parser.add_argument('--min-balls',type=int,default=12)
    parser.add_argument('--out',type=Path,default=ROOT/'outputs')
    args=parser.parse_args()
    run(args.db,args.min_balls,args.out)
