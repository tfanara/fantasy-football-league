from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from season_config import CURRENT_SEASON, detect_latest_completed_week

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
PLAYER_WEEK = DATA / "matchups" / "player_week_stats"
NEWS = DATA / "news" / str(CURRENT_SEASON)

MATCHUPS = DATA / "all_matchups_clean.csv"
TEAM_GAMES = HISTORY / "team_games.csv"
SEASON_RECORDS = HISTORY / "season_records.csv"
STANDINGS = DATA / "all_standings.csv"
WEEKLY_LINEUPS = PLAYER_WEEK / "all_weekly_lineups.csv"

ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}

def load(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def canon(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    return ALIASES.get(value, value)

def normalize(df):
    df = df.copy()
    for col in ["team", "opponent", "team_1", "team_2", "fantasy_team"]:
        if col in df.columns:
            df[col] = df[col].map(canon)
    return df

def historical_h2h(games, team, opponent, year, week):
    g = games[(games["team"] == team) & (games["opponent"] == opponent)].copy()
    g = g[(g["year"] < year) | ((g["year"] == year) & (g["week"] < week))]
    return {
        "games": int(len(g)),
        "record": f"{int((g.result == 'W').sum())}-{int((g.result == 'L').sum())}-{int((g.result == 'T').sum())}",
    }

def prior_streak(games, team, result, year, week):
    g = games[games["team"] == team].copy()
    g = g[(g["year"] < year) | ((g["year"] == year) & (g["week"] < week))]
    g = g.sort_values(["year", "week"])
    run = 0
    for value in reversed(g["result"].astype(str).tolist()):
        if value != result:
            break
        run += 1
    return run

def player_facts(lineups, year, week):
    required = {"year", "week", "fantasy_points"}
    if lineups.empty or not required.issubset(lineups.columns):
        return {}
    w = lineups[
        (pd.to_numeric(lineups["year"], errors="coerce") == year)
        & (pd.to_numeric(lineups["week"], errors="coerce") == week)
    ].copy()
    if "is_starter" in w.columns:
        w = w[w["is_starter"].astype(str).str.lower().isin(["true", "1", "yes"])]
    w["fantasy_points"] = pd.to_numeric(w["fantasy_points"], errors="coerce")
    w = w[w["fantasy_points"].notna()]
    if w.empty:
        return {}
    top = w.sort_values("fantasy_points", ascending=False).iloc[0]
    return {"top_starter": {
        "player": str(top.get("player", "")),
        "team": str(top.get("fantasy_team", "")),
        "position": str(top.get("position", "")),
        "points": round(float(top["fantasy_points"]), 2),
    }}

def main():
    matchups = normalize(load(MATCHUPS))
    if matchups.empty:
        raise RuntimeError("Canonical matchup master is missing or empty.")

    state = detect_latest_completed_week(matchups)
    week = int(state.latest_completed_week or 0)
    if week == 0:
        print(f"PASS — no completed {CURRENT_SEASON} week; no weekly news context generated.")
        return

    games = normalize(load(TEAM_GAMES))
    if games.empty:
        raise RuntimeError("data/history/team_games.csv is missing or empty.")

    for col in ["year", "week", "points_for", "points_against"]:
        games[col] = pd.to_numeric(games[col], errors="coerce")

    wg = games[(games["year"] == CURRENT_SEASON) & (games["week"] == week)].copy()
    if len(wg) != 12 or wg["team"].nunique() != 12:
        raise RuntimeError(
            f"{CURRENT_SEASON} Week {week}: expected 12 team-game rows / 12 teams; "
            f"found {len(wg)} / {wg['team'].nunique()}."
        )

    stories, seen = [], set()
    for _, row in wg.iterrows():
        a, b = str(row["team"]), str(row["opponent"])
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        other_rows = wg[(wg["team"] == b) & (wg["opponent"] == a)]
        if other_rows.empty:
            raise RuntimeError(f"Missing reciprocal team-game row for {a} vs {b}.")
        other = other_rows.iloc[0]
        winner, loser = (row, other) if row["points_for"] >= other["points_for"] else (other, row)
        stories.append({
            "winner": str(winner["team"]),
            "loser": str(loser["team"]),
            "winner_score": round(float(winner["points_for"]), 2),
            "loser_score": round(float(loser["points_for"]), 2),
            "margin": round(abs(float(winner["points_for"]) - float(loser["points_for"])), 2),
            "historical_h2h_before_game": historical_h2h(
                games, str(winner["team"]), str(loser["team"]), CURRENT_SEASON, week
            ),
        })

    if len(stories) != 6:
        raise RuntimeError(f"Expected 6 matchup stories; found {len(stories)}.")

    high = wg.sort_values("points_for", ascending=False).iloc[0]
    low = wg.sort_values("points_for").iloc[0]

    snapped = []
    for _, row in wg.iterrows():
        result = str(row["result"])
        opposite = {"W": "L", "L": "W"}.get(result)
        if not opposite:
            continue
        run = prior_streak(games, str(row["team"]), opposite, CURRENT_SEASON, week)
        if run >= 2:
            snapped.append({
                "team": str(row["team"]),
                "streak_type": "losing" if opposite == "L" else "winning",
                "length": run,
            })

    standings = normalize(load(STANDINGS))
    standings_rows = []
    if not standings.empty and "year" in standings.columns:
        s = standings[pd.to_numeric(standings["year"], errors="coerce") == CURRENT_SEASON]
        standings_rows = s.to_dict("records")

    season_records = normalize(load(SEASON_RECORDS))
    season_rows = []
    if not season_records.empty and "year" in season_records.columns:
        s = season_records[pd.to_numeric(season_records["year"], errors="coerce") == CURRENT_SEASON]
        keep = [c for c in ["team","wins","losses","ties","points_for","points_against","point_diff","win_pct"] if c in s.columns]
        season_rows = s[keep].to_dict("records")

    packet = {
        "schema_version": 1,
        "season": CURRENT_SEASON,
        "week": week,
        "editorial_guardrail": "AI may add satire, but factual claims must be supported by this packet. Predictions must be labeled.",
        "week_summary": {
            "highest_scoring_team": {"team": str(high["team"]), "points": round(float(high["points_for"]), 2)},
            "lowest_scoring_team": {"team": str(low["team"]), "points": round(float(low["points_for"]), 2)},
            "closest_game": min(stories, key=lambda x: x["margin"]),
            "biggest_blowout": max(stories, key=lambda x: x["margin"]),
        },
        "matchups": sorted(stories, key=lambda x: x["margin"]),
        "player_facts": player_facts(normalize(load(WEEKLY_LINEUPS)), CURRENT_SEASON, week),
        "streaks_snapped": snapped,
        "standings": standings_rows,
        "season_team_context": season_rows,
        "planned_adapters": {
            "bad_beats": "Phase 1B: connect validated bad-beat output",
            "managerial_decisions": "Phase 1B: connect validated lineup-efficiency output",
            "records_and_milestones": "Phase 1B: connect Records-page watch logic",
            "future_matchups": "Phase 1B: connect authoritative schedule source",
            "power_rankings": "Phase 2: deterministic ranking model",
        },
    }

    NEWS.mkdir(parents=True, exist_ok=True)
    out = NEWS / f"week_{week:02d}_context.json"
    out.write_text(json.dumps(packet, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"PASS — Weekly News Intelligence: {CURRENT_SEASON} Week {week}")
    print("PASS — 6 matchup stories / 12 teams validated")
    print(f"PASS — wrote {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()