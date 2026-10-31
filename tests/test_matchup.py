import importlib.util
import json
import math
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.matchup import MatchupModel, Totals, blend, combine_wicket_rates

class MatchupChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = MatchupModel(through_season=2021)

    def test_shrinkage_hand_calculation(self):
        # Prior=1.5, observed=20/10=2.0, direct weight=10/(30+10)=25%.
        self.assertAlmostEqual(blend(1.5,20,10,30),1.625)
        self.assertAlmostEqual(blend(1.5,0,0,30),1.5)
        self.assertAlmostEqual(blend(1.5,60,30,30),1.75)

    def test_wicket_combination(self):
        self.assertAlmostEqual(combine_wicket_rates(.05,.05,.05),.05)
        self.assertAlmostEqual(combine_wicket_rates(.10,.05,.05),.10)
        for b in (0,.01,.5,1):
            for p in (0,.05,.9,1):
                self.assertTrue(0<=combine_wicket_rates(b,p,.05)<=1)

    def test_no_head_to_head_uses_profile(self):
        m=self.model
        pair=next((b,p,ph) for b,ph in m.batters for p,k in m.bowlers
            if k==ph and b!=p and (b,p,ph) not in m.matchups)
        b,p,ph=pair
        phase={1:'Powerplay',2:'Middle',3:'Death'}[ph]
        r=m.predict(m.names_by_key[b],m.names_by_key[p],phase)
        self.assertEqual(r['matchup_balls'],0)
        self.assertEqual(r['direct_weight_runs'],0)
        self.assertAlmostEqual(r['expected_runs_per_legal_ball'],r['profile_expected_runs'])

    def test_wicket_value_only_changes_score(self):
        args=('V Kohli','JJ Bumrah','Death')
        a=self.model.predict(*args,wicket_value=0)
        b=self.model.predict(*args,wicket_value=20)
        self.assertEqual(a['expected_runs_per_legal_ball'],b['expected_runs_per_legal_ball'])
        self.assertAlmostEqual(a['score']-b['score'],20*a['wicket_probability_per_legal_ball'])

    def test_future_seasons_cannot_affect_predictions(self):
        # Remove all post-2021 deliveries in an isolated copy and require identical estimates.
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'without_future.sqlite'
            shutil.copy2(self.model.db_path,target)
            con=sqlite3.connect(target)
            try:
                con.execute('DELETE FROM fact_deliveries WHERE match_key IN '
                    '(SELECT match_key FROM dim_match WHERE season>2021)')
                con.commit()
            finally:
                con.close()
            alternative=MatchupModel(target,through_season=2021)
            for phase in ('Powerplay','Middle','Death'):
                args=('V Kohli','JJ Bumrah',phase)
                self.assertEqual(self.model.predict(*args),alternative.predict(*args))

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            blend(1,1,1,0)
        with self.assertRaises(ValueError):
            self.model.predict('V Kohli','V Kohli','Death')
        with self.assertRaises(ValueError):
            self.model.predict('V Kohli','JJ Bumrah','Death',float('nan'))

if __name__=='__main__':
    unittest.main()
