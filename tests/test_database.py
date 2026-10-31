"""Check cricket edge cases in the real loaded source, independently of ETL."""
import sqlite3
import unittest
from pathlib import Path

class DatabaseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(Path(__file__).resolve().parents[1]/'data/deathovers.sqlite')

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def count(self, where):
        return self.db.execute('SELECT COUNT(*) FROM fact_deliveries WHERE '+where).fetchone()[0]

    def test_phase_boundaries(self):
        self.assertEqual(self.count('(over_index=5 AND phase_key<>1) OR '
            '(over_index=6 AND phase_key<>2) OR (over_index=14 AND phase_key<>2) OR '
            '(over_index=15 AND phase_key<>3)'),0)

    def test_runouts_and_retirements(self):
        self.assertGreater(self.count("dismissal_kind='run out'"),0)
        self.assertEqual(self.count("dismissal_kind IN ('run out','retired hurt',"
            "'retired out','obstructing the field') AND bowler_wicket<>0"),0)

    def test_illegal_deliveries(self):
        self.assertGreater(self.count("extras_type IN ('wides','noballs')"),0)
        self.assertEqual(self.count("extras_type IN ('wides','noballs') AND legal_ball<>0"),0)

    def test_byes_not_charged(self):
        self.assertEqual(self.count("extras_type IN ('byes','legbyes','penalty') "
            'AND bowler_runs<>batsman_runs'),0)

    def test_aggregates_exclude_super_overs(self):
        expected=self.db.execute('SELECT SUM(legal_ball),SUM(CASE WHEN legal_ball=1 '
            'THEN batsman_runs ELSE 0 END) FROM fact_deliveries WHERE innings<=2').fetchone()
        actual=self.db.execute('SELECT SUM(balls),SUM(model_runs) FROM agg_matchup').fetchone()
        self.assertEqual(expected,actual)
        self.assertGreater(self.count('is_super_over=1'),0)

if __name__=='__main__':
    unittest.main()
