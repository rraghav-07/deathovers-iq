-- Run in a SQLite client against data/deathovers.sqlite.
SELECT COUNT(*) AS deliveries FROM fact_deliveries;
SELECT season,COUNT(*) AS matches FROM dim_match GROUP BY season ORDER BY season;
-- League scoring on legal deliveries; not official economy.
SELECT p.name, SUM(a.balls) AS legal_balls,
 ROUND(1.0*SUM(a.model_runs)/SUM(a.balls),3) AS bat_runs_per_legal_ball,
 ROUND(100.0*SUM(a.model_wickets)/SUM(a.balls),2) AS wicket_percent
FROM agg_league_phase a JOIN dim_phase p USING(phase_key)
GROUP BY p.phase_key ORDER BY p.phase_key;
-- Example matchup, restricted to initial training seasons.
SELECT a.season,b.name AS batter,w.name AS bowler,p.name AS phase,
 a.balls,a.model_runs,a.model_wickets
FROM agg_matchup a
JOIN dim_player b ON b.player_key=a.batter_key
JOIN dim_player w ON w.player_key=a.bowler_key
JOIN dim_phase p USING(phase_key)
WHERE b.name='V Kohli' AND w.name='JJ Bumrah' AND a.season<=2021
ORDER BY a.season,a.phase_key;
