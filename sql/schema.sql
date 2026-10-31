PRAGMA foreign_keys = ON;
CREATE TABLE dim_player (
 player_key INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE dim_match (
 match_key INTEGER PRIMARY KEY, season_label TEXT NOT NULL,
 season INTEGER NOT NULL, match_date TEXT NOT NULL, venue TEXT,
 team1 TEXT NOT NULL, team2 TEXT NOT NULL
);
CREATE TABLE dim_phase (
 phase_key INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 first_over INTEGER NOT NULL, last_over INTEGER NOT NULL
);
INSERT INTO dim_phase VALUES (1,'Powerplay',1,6),(2,'Middle',7,15),(3,'Death',16,20);
CREATE TABLE fact_deliveries (
 delivery_key INTEGER PRIMARY KEY,
 match_key INTEGER NOT NULL REFERENCES dim_match(match_key),
 batter_key INTEGER NOT NULL REFERENCES dim_player(player_key),
 bowler_key INTEGER NOT NULL REFERENCES dim_player(player_key),
 phase_key INTEGER NOT NULL REFERENCES dim_phase(phase_key),
 innings INTEGER NOT NULL CHECK(innings BETWEEN 1 AND 6),
 over_index INTEGER NOT NULL CHECK(over_index BETWEEN 0 AND 19),
 ball INTEGER NOT NULL CHECK(ball > 0),
 batting_team TEXT NOT NULL, bowling_team TEXT NOT NULL,
 batsman_runs INTEGER NOT NULL CHECK(batsman_runs >= 0),
 extra_runs INTEGER NOT NULL CHECK(extra_runs >= 0),
 total_runs INTEGER NOT NULL CHECK(total_runs = batsman_runs + extra_runs),
 extras_type TEXT, dismissal_kind TEXT,
 is_wicket INTEGER NOT NULL CHECK(is_wicket IN (0,1)),
 bowler_wicket INTEGER NOT NULL CHECK(bowler_wicket IN (0,1)),
 legal_ball INTEGER NOT NULL CHECK(legal_ball IN (0,1)),
 bowler_runs INTEGER NOT NULL CHECK(bowler_runs >= 0),
 is_super_over INTEGER NOT NULL CHECK(is_super_over IN (0,1))
);
CREATE INDEX idx_fact_match ON fact_deliveries(match_key);
CREATE INDEX idx_fact_matchup ON fact_deliveries(batter_key,bowler_key,phase_key);
CREATE INDEX idx_fact_bowler_phase ON fact_deliveries(bowler_key,phase_key);
CREATE INDEX idx_fact_phase ON fact_deliveries(phase_key);
CREATE INDEX idx_match_season ON dim_match(season);
