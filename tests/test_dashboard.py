from pathlib import Path
import unittest

try:
    from streamlit.testing.v1 import AppTest
    import plotly
    AVAILABLE=True
except ImportError:
    AVAILABLE=False

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(AVAILABLE,'Install requirements.txt for dashboard tests.')
class DashboardChecks(unittest.TestCase):
    def app(self):
        return AppTest.from_file(ROOT/'app/streamlit_app.py',default_timeout=30).run()

    def assert_clean(self,app):
        self.assertEqual(len(app.exception),0,[e.message for e in app.exception])

    def test_default_shortlist_matches_configured_model(self):
        app=self.app()
        self.assert_clean(app)
        self.assertTrue(any('Prefer SP Narine' in x.value for x in app.info))
        self.assertEqual(len(app.dataframe[0].value),4)

    def test_empty_selection_and_single_selection(self):
        app=self.app()
        app.multiselect(key='captain_bowlers').set_value([]).run()
        self.assert_clean(app)
        self.assertTrue(any('Select at least one' in x.value for x in app.info))
        app.multiselect(key='captain_bowlers').set_value(['JJ Bumrah']).run()
        self.assert_clean(app)
        self.assertEqual(len(app.dataframe[0].value),1)

    def test_wicket_slider_and_phase_change(self):
        app=self.app()
        app.selectbox(key='captain_phase').set_value('Middle').run()
        app.slider(key='wicket_value').set_value(0).run()
        self.assert_clean(app)
        frame=app.dataframe[0].value
        self.assertTrue((abs(frame['Score']-frame['Bat runs / legal ball'])<.0011).all())
        self.assertTrue(frame['Bat runs / legal ball'].is_monotonic_increasing)

    def test_profiles_and_sparse_history(self):
        app=self.app()
        for page in ('Batter Profile','Bowler Profile'):
            app.radio(key='page').set_value(page).run()
            self.assert_clean(app)
            self.assertGreater(len(app.dataframe[0].value),0)
            app.slider(key='profile_minimum').set_value(60).run()
            self.assert_clean(app)
        app.radio(key='page').set_value('Captain’s Cheat Sheet').run()
        self.assert_clean(app)

    def test_validation_matches_measured_results(self):
        app=self.app()
        app.radio(key='page').set_value('Model Validation').run()
        self.assert_clean(app)
        self.assertEqual(app.metric[0].value,'4.19%')
        self.assertEqual(len(app.dataframe[0].value),4)
        app.radio(key='validation_population').set_value('All eligible groups').run()
        self.assert_clean(app)
        self.assertEqual(len(app.dataframe[0].value),3)
        self.assertTrue(any('Raw H2H cannot predict' in x.value for x in app.info))

if __name__=='__main__':
    unittest.main()
