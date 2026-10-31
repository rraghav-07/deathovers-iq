"""Build an audited SQLite database from the supplied 2008–2024 CSV format.

Uses Python's standard library only. Run from any working directory.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from contextlib import closing
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
CREDITED = {'caught', 'bowled', 'lbw', 'stumped', 'caught and bowled', 'hit wicket'}
EXTRAS = {'', 'wides', 'noballs', 'byes', 'legbyes', 'penalty'}

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def require(condition, message):
    if not condition:
        raise ValueError(message)

def build(raw_dir, db_path):
    paths = [raw_dir / 'matches.csv', raw_dir / 'deliveries.csv']
    matches, deliveries = map(read_csv, paths)
    require(matches and deliveries, 'Both CSV files must contain records.')
    require({'id','date','season','venue','team1','team2'} <= matches[0].keys(),
            'matches.csv has an unsupported set of columns.')
    fields = {'match_id','inning','over','ball','batter','bowler','batting_team',
              'bowling_team','batsman_runs','extra_runs','total_runs','extras_type',
              'dismissal_kind','is_wicket'}
    require(fields <= deliveries[0].keys(), 'deliveries.csv has unsupported columns.')
    match_ids = [int(r['id']) for r in matches]
    require(len(set(match_ids)) == len(match_ids), 'Duplicate match IDs found.')
    require({int(r['match_id']) for r in deliveries} <= set(match_ids),
            'Some deliveries have no matching match record.')
    players = sorted({r[k].strip() for r in deliveries for k in ('batter','bowler')})
    require(all(p and p != 'NA' for p in players), 'Missing player names found.')
    player_keys = {p: i+1 for i,p in enumerate(players)}
    # Build in a temporary database: a failed import cannot damage an existing one.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(suffix='.sqlite', dir=db_path.parent)
    os.close(handle)
    try:
        # SQLite's transaction context commits/rolls back but does NOT close.
        # Close explicitly before renaming or deleting the file on Windows.
        with closing(sqlite3.connect(temp_name)) as con, con:
            con.executescript((ROOT/'sql/schema.sql').read_text())
            con.executemany('INSERT INTO dim_player VALUES (?,?)',
                            [(v,k) for k,v in player_keys.items()])
            con.executemany('INSERT INTO dim_match VALUES (?,?,?,?,?,?,?)', [
                (int(r['id']),r['season'],date.fromisoformat(r['date']).year,
                 r['date'],r['venue'],r['team1'],r['team2']) for r in matches])
            batch = []
            for index,r in enumerate(deliveries, 1):
                extra = r['extras_type'].strip()
                require(extra in EXTRAS, f'Unknown extras type at row {index}: {extra}')
                inning, over, ball = (int(r[k]) for k in ('inning','over','ball'))
                bat, ex, total = (int(r[k]) for k in ('batsman_runs','extra_runs','total_runs'))
                kind = r['dismissal_kind'].strip()
                wicket = int(r['is_wicket'])
                credited = int(kind in CREDITED)
                require(not credited or wicket == 1, f'Inconsistent wicket at row {index}')
                legal = int(extra not in {'wides','noballs'})
                charged = bat + (ex if extra in {'wides','noballs'} else 0)
                phase = 1 if over <= 5 else 2 if over <= 14 else 3
                batch.append((index,int(r['match_id']),player_keys[r['batter'].strip()],
                    player_keys[r['bowler'].strip()],phase,inning,over,ball,
                    r['batting_team'],r['bowling_team'],bat,ex,total,extra or None,
                    None if kind in {'','NA'} else kind,wicket,credited,legal,charged,
                    int(inning > 2)))
            con.executemany('INSERT INTO fact_deliveries VALUES (' + ','.join('?'*20) + ')', batch)
            con.executescript((ROOT/'sql/aggregates.sql').read_text())
            require(not con.execute('PRAGMA foreign_key_check').fetchall(), 'Foreign key check failed.')
            require(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Integrity check failed.')
            normal, super_count, legal, wickets = con.execute('''
                SELECT SUM(is_super_over=0), SUM(is_super_over=1),
                SUM(CASE WHEN is_super_over=0 THEN legal_ball ELSE 0 END),
                SUM(CASE WHEN is_super_over=0 THEN bowler_wicket ELSE 0 END)
                FROM fact_deliveries''').fetchone()
            aggregate_balls = con.execute('SELECT SUM(balls) FROM agg_matchup').fetchone()[0]
            require(aggregate_balls == legal, 'Aggregate legal-ball reconciliation failed.')
            phases = con.execute('''SELECT p.name,SUM(a.balls),SUM(a.model_runs),
                SUM(a.model_wickets) FROM agg_league_phase a JOIN dim_phase p USING(phase_key)
                GROUP BY p.phase_key ORDER BY p.phase_key''').fetchall()
            require(sum(p[1] for p in phases) == legal, 'Phase reconciliation failed.')
            years = [date.fromisoformat(r['date']).year for r in matches]
            report = dict(matches=len(matches),raw_deliveries=len(deliveries),
                normal_deliveries=normal,super_over_deliveries_excluded=super_count,
                legal_balls=legal,players=len(players),bowler_wickets=wickets,
                first_season=min(years),last_season=max(years),
                foreign_key_check='passed',integrity_check='passed',
                aggregate_reconciliation='passed',phase_totals=phases,
                source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        os.replace(temp_name, db_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    output = ROOT/'outputs/data_quality.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(f'\nDatabase ready: {db_path}\nAudit report: {output}')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    parser.add_argument('--db',type=Path,default=ROOT/'data/deathovers.sqlite')
    args = parser.parse_args()
    build(args.raw_dir.resolve(),args.db.resolve())
