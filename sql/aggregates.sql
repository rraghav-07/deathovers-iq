-- Retain season in EVERY aggregate so future model queries can filter training years.
-- Super Overs stay in the fact table for auditing but never enter standard profiles.
CREATE VIEW agg_matchup AS
SELECT m.season, f.batter_key, f.bowler_key, f.phase_key,
 COUNT(*) AS deliveries, SUM(legal_ball) AS balls,
 SUM(batsman_runs) AS runs, SUM(bowler_runs) AS runs_conceded,
 SUM(bowler_wicket) AS wickets,
 SUM(CASE WHEN legal_ball=1 THEN batsman_runs ELSE 0 END) AS model_runs,
 SUM(CASE WHEN legal_ball=1 THEN bowler_wicket ELSE 0 END) AS model_wickets
FROM fact_deliveries f JOIN dim_match m USING(match_key)
WHERE is_super_over=0
GROUP BY m.season,f.batter_key,f.bowler_key,f.phase_key;
CREATE VIEW agg_batter_phase AS
SELECT season,batter_key,phase_key,SUM(balls) AS balls,SUM(runs) AS runs,
 SUM(wickets) AS wickets,SUM(model_runs) AS model_runs,
 SUM(model_wickets) AS model_wickets
FROM agg_matchup GROUP BY season,batter_key,phase_key;
CREATE VIEW agg_bowler_phase AS
SELECT season,bowler_key,phase_key,SUM(balls) AS balls,
 SUM(runs_conceded) AS runs_conceded,SUM(wickets) AS wickets,
 SUM(model_runs) AS model_runs,SUM(model_wickets) AS model_wickets
FROM agg_matchup GROUP BY season,bowler_key,phase_key;
CREATE VIEW agg_league_phase AS
SELECT season,phase_key,SUM(balls) AS balls,SUM(model_runs) AS model_runs,
 SUM(model_wickets) AS model_wickets
FROM agg_matchup GROUP BY season,phase_key;
-- Window-function example: rank bowlers by wickets within season and phase.
CREATE VIEW ranked_bowler_phase AS
SELECT *,DENSE_RANK() OVER (
 PARTITION BY season,phase_key ORDER BY wickets DESC
) AS wicket_rank FROM agg_bowler_phase;
