import csv
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.backtest import metrics, comparison, relative_improvement, predict_groups

def fixture(actual,predicted,balls,wickets,probability,history):
    return dict(actual_runs=actual,balls=balls,wickets=wickets,
        training_matchup_balls=history,
        run_predictions={m:predicted for m in ('League','Bowler','Shrinkage','Raw H2H')},
        wicket_predictions={m:probability for m in ('League','Bowler','Shrinkage','Raw H2H')})

class BacktestChecks(unittest.TestCase):
    def test_hand_calculated_mae_and_brier(self):
        a=fixture(1,1.5,10,1,.2,1)
        b=fixture(2,1.75,30,0,.1,1)
        result=metrics([a,b],'Shrinkage')
        self.assertAlmostEqual(result['mae'],.375)
        self.assertAlmostEqual(result['ball_weighted_mae'],.3125)
        # 10*.04-2*.2+1 + 30*.01 = 1.3, across 40 deliveries.
        self.assertAlmostEqual(result['wicket_brier'],1.3/40)

    def test_shared_subset_and_missing_history(self):
        a=fixture(1,1.5,12,1,.1,1)
        b=fixture(1,1.5,12,0,.1,0)
        b['run_predictions']['Raw H2H']=None
        b['wicket_predictions']['Raw H2H']=None
        common=comparison([a,b])
        self.assertEqual(common['groups'],1)
        self.assertTrue(all(v['groups']==1 for v in common['methods'].values()))
        self.assertEqual(comparison([a,b],False)['groups'],2)
        with self.assertRaises(ValueError):
            metrics([a,b],'Raw H2H')

    def test_improvement_sign(self):
        self.assertAlmostEqual(relative_improvement(.5,.4),20)
        self.assertAlmostEqual(relative_improvement(.4,.5),-25)

    def test_evaluation_overlap_rejected(self):
        class Stub:
            through_season=2022
        with self.assertRaises(ValueError):
            predict_groups(Stub(),[{'season':2022}])

    def test_saved_predictions_reproduce_primary_mae(self):
        path=ROOT/'outputs/test_predictions.csv'
        if not path.exists():
            self.skipTest('Run model/backtest.py to create the evaluation artifacts.')
        report=json.loads((ROOT/'outputs/backtest_results.json').read_text())
        with path.open(newline='',encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        common=[r for r in rows if int(r['training_matchup_balls'])>0]
        self.assertEqual(len(rows),report['eligible_test_groups'])
        self.assertEqual(len(common),report['common_history']['groups'])
        for method in ('League','Bowler','Raw H2H','Shrinkage'):
            mae=sum(abs(float(r['runs_'+method])-float(r['runs'])/int(r['balls']))
                    for r in common)/len(common)
            self.assertAlmostEqual(mae,report['common_history']['methods'][method]['mae'])

if __name__=='__main__':
    unittest.main()
