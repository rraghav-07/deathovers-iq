"""Phase-specific player profiles blended with head-to-head history.

Targets: bat runs and bowler-credited wickets per legal delivery.
All statistics are filtered to the explicit training cutoff before fitting.
"""
import argparse
from contextlib import closing
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PHASES = {'Powerplay': 1, 'Middle': 2, 'Death': 3}

@dataclass(frozen=True)
class Totals:
    balls: int = 0
    runs: int = 0
    wickets: int = 0

def blend(expected, events, balls, strength):
    """strength acts like this many prior legal deliveries."""
    if not all(math.isfinite(x) for x in (expected,events,balls,strength)):
        raise ValueError('Inputs must be finite.')
    if min(expected,events,balls) < 0 or strength <= 0:
        raise ValueError('Inputs must be nonnegative and strength positive.')
    return (strength * expected + events) / (strength + balls)

def combine_wicket_rates(batter_rate, bowler_rate, league_rate):
    """Combine event odds relative to league odds; output stays in [0, 1]."""
    eps = 1e-9
    def odds(p):
        p = min(1-eps,max(eps,p))
        return p/(1-p)
    matchup_odds = odds(batter_rate)*odds(bowler_rate)/odds(league_rate)
    return matchup_odds/(1+matchup_odds)

class MatchupModel:
    def __init__(self, db_path=ROOT/'data/deathovers.sqlite', through_season=2021,
                 k_runs=30.0, k_wickets=30.0, profile_strength=60.0):
        for value in (k_runs,k_wickets,profile_strength):
            if not math.isfinite(value) or value<=0:
                raise ValueError('Shrinkage strengths must be finite and positive.')
        self.db_path = Path(db_path).resolve()
        if not self.db_path.is_file():
            raise FileNotFoundError(f'Database missing: {self.db_path}. Run etl/load_data.py first.')
        self.through_season = int(through_season)
        self.k_runs,self.k_wickets = k_runs,k_wickets
        self.profile_strength = profile_strength
        self.league,self.batters,self.bowlers,self.matchups = {},{},{},{}
        with closing(sqlite3.connect(self.db_path.as_uri()+'?mode=ro',uri=True)) as con:
            self.names = dict(con.execute('SELECT name,player_key FROM dim_player'))
            self.names_by_key = {v:k for k,v in self.names.items()}
            queries = (
                ('phase_key',self.league),
                ('batter_key,phase_key',self.batters),
                ('bowler_key,phase_key',self.bowlers),
                ('batter_key,bowler_key,phase_key',self.matchups),
            )
            for keys,destination in queries:
                rows = con.execute(f'''SELECT {keys},SUM(balls),SUM(model_runs),SUM(model_wickets)
                    FROM agg_matchup WHERE season<=? GROUP BY {keys}''',(self.through_season,))
                width = len(keys.split(','))
                for row in rows:
                    key = row[0] if width==1 else tuple(row[:width])
                    destination[key] = Totals(*row[width:])
        if any(self.league.get(p,Totals()).balls==0 for p in PHASES.values()):
            raise ValueError('Training cutoff does not provide legal balls in every phase.')

    def player_key(self,name):
        if name not in self.names:
            raise ValueError(f'Unknown player {name!r}. Use exact dataset names; run --list-players.')
        return self.names[name]

    def phase_key(self,phase):
        if phase not in PHASES:
            raise ValueError('Phase must be Powerplay, Middle or Death.')
        return PHASES[phase]

    def profile(self,totals,league):
        return (blend(league.runs/league.balls,totals.runs,totals.balls,self.profile_strength),
                blend(league.wickets/league.balls,totals.wickets,totals.balls,self.profile_strength))

    def predict(self,batter,bowler,phase,wicket_value=20.0):
        if not math.isfinite(wicket_value) or wicket_value<0:
            raise ValueError('Wicket value must be finite and nonnegative.')
        b,p,ph = self.player_key(batter),self.player_key(bowler),self.phase_key(phase)
        if b==p:
            raise ValueError('Batter and bowler must be different players.')
        league = self.league[ph]
        bt,pt = self.batters.get((b,ph),Totals()),self.bowlers.get((p,ph),Totals())
        head = self.matchups.get((b,p,ph),Totals())
        br,bw = self.profile(bt,league)
        pr,pw = self.profile(pt,league)
        league_runs = league.runs/league.balls
        league_wickets = league.wickets/league.balls
        expected_runs = br*pr/league_runs if league_runs>0 else 0.0
        expected_wickets = combine_wicket_rates(bw,pw,league_wickets)
        runs = blend(expected_runs,head.runs,head.balls,self.k_runs)
        wickets = blend(expected_wickets,head.wickets,head.balls,self.k_wickets)
        # These are disclosed sample-count labels, not calibrated confidence levels.
        support = 'No direct history' if head.balls==0 else 'Limited' if head.balls<30 else 'More direct history'
        return dict(batter=batter,bowler=bowler,phase=phase,
            through_season=self.through_season,expected_runs_per_legal_ball=runs,
            wicket_probability_per_legal_ball=wickets,
            bat_runs_per_six_legal_balls=6*runs,
            score=runs-wicket_value*wickets,wicket_value=wicket_value,
            profile_expected_runs=expected_runs,profile_expected_wickets=expected_wickets,
            league_runs_per_legal_ball=league_runs,
            fewer_bat_runs_per_six_vs_league=6*(league_runs-runs),
            raw_h2h_runs_per_ball=head.runs/head.balls if head.balls else None,
            raw_h2h_wicket_probability=head.wickets/head.balls if head.balls else None,
            bowler_baseline_runs_per_ball=pt.runs/pt.balls if pt.balls else league_runs,
            matchup_balls=head.balls,batter_phase_balls=bt.balls,bowler_phase_balls=pt.balls,
            direct_weight_runs=head.balls/(head.balls+self.k_runs),
            direct_weight_wickets=head.balls/(head.balls+self.k_wickets),
            support=support,profile_fallback=bt.balls==0 or pt.balls==0,
            k_runs=self.k_runs,k_wickets=self.k_wickets,
            profile_strength=self.profile_strength)

    def recommend(self,batter,bowlers,phase,wicket_value=20.0):
        if not bowlers:
            raise ValueError('Select at least one available bowler.')
        rows = [self.predict(batter,p,phase,wicket_value) for p in dict.fromkeys(bowlers)]
        return sorted(rows,key=lambda r:(r['score'],r['expected_runs_per_legal_ball'],r['bowler']))

    def available_bowlers(self,phase):
        ph = self.phase_key(phase)
        return sorted(self.names_by_key[p] for (p,k),v in self.bowlers.items() if k==ph and v.balls>0)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'data/deathovers.sqlite')
    parser.add_argument('--through',type=int)
    parser.add_argument('--config',type=Path,help='Optional validation-selected model_config.json')
    parser.add_argument('--batter',default='V Kohli')
    parser.add_argument('--bowlers',nargs='+',default=['JJ Bumrah','R Ashwin','RA Jadeja','SP Narine'])
    parser.add_argument('--phase',choices=PHASES,default='Death')
    parser.add_argument('--wicket-value',type=float,default=20.0)
    parser.add_argument('--k-runs',type=float)
    parser.add_argument('--k-wickets',type=float)
    parser.add_argument('--profile-strength',type=float)
    parser.add_argument('--list-players',action='store_true')
    args = parser.parse_args()
    config=json.loads(args.config.read_text()) if args.config else {}
    # Explicit command-line values override config; legacy defaults stay reproducible.
    for argument,key,default in (('through','through_season',2021),
        ('k_runs','k_runs',30.0),('k_wickets','k_wickets',30.0),
        ('profile_strength','profile_strength',60.0)):
        if getattr(args,argument) is None:
            setattr(args,argument,config.get(key,default))
    model = MatchupModel(args.db,args.through,args.k_runs,args.k_wickets,args.profile_strength)
    if args.list_players:
        print('Bowlers with training-phase experience:')
        print('\n'.join(model.available_bowlers(args.phase)))
        return
    rows = model.recommend(args.batter,args.bowlers,args.phase,args.wicket_value)
    label='CONFIGURED MODEL' if args.config else 'PROVISIONAL MODEL'
    print(f'{label} | training through {args.through} | {args.phase}')
    print('Targets: bat runs and bowler wickets per LEGAL delivery; extras are not predicted.')
    print('Lower score ranks first. Wicket value is an assumption, not a learned value.\n')
    print(f'{"Rank":<5}{"Bowler":<20}{"Runs/ball":>10}{"Wicket %":>11}{"H2H balls":>11}{"H2H weight":>12}{"Score":>10}')
    for rank,r in enumerate(rows,1):
        print(f'{rank:<5}{r["bowler"]:<20}{r["expected_runs_per_legal_ball"]:>10.3f}'
              f'{100*r["wicket_probability_per_legal_ball"]:>11.2f}{r["matchup_balls"]:>11}'
              f'{100*r["direct_weight_runs"]:>11.1f}%{r["score"]:>10.3f}')
    best = rows[0]
    print(f'\nFirst among your selected bowlers: {best["bowler"]}.')
    print(f'Direct history: {best["matchup_balls"]} legal balls; support: {best["support"]}.')
    if best['profile_fallback']:
        print('At least one player has no training-phase profile; league fallback was used.')
    print('Sample labels are descriptive; predictive confidence has not been calibrated.')
    path = ROOT/'outputs/example_recommendation.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(rows,indent=2)+'\n')
    print(f'Detailed estimates saved to: {path}')

if __name__=='__main__':
    main()
