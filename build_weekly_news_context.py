from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from season_config import CURRENT_SEASON, detect_latest_completed_week

try:
    from team_aliases import canonical_team as _shared_canonical_team
except ImportError:
    _shared_canonical_team = lambda value: value


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
PLAYER_WEEK = DATA / "matchups" / "player_week_stats"
PLAYER_ANALYSIS = PLAYER_WEEK / "analysis"
ANALYSIS = DATA / "analysis"
NEWS = DATA / "news" / str(CURRENT_SEASON)

MATCHUPS = DATA / "all_matchups_clean.csv"
TEAM_GAMES = HISTORY / "team_games.csv"
SEASON_RECORDS = HISTORY / "season_records.csv"
STANDINGS = DATA / "all_standings.csv"
UPCOMING_MATCHUPS = DATA / str(CURRENT_SEASON) / "upcoming_matchups.csv"
TRANSACTIONS = DATA / str(CURRENT_SEASON) / "transactions.csv"

# Prefer the season-spanning master produced by the weekly player pipeline.
WEEKLY_LINEUP_CANDIDATES = [
    PLAYER_WEEK / "all_weekly_lineups_2017_2026.csv",
    PLAYER_WEEK / "all_weekly_lineups.csv",
]

BAD_BEATS = ANALYSIS / "bad_beat_team_week.csv"
LINEUP_EFFICIENCY = PLAYER_ANALYSIS / "lineup_efficiency_team_week.csv"

# Defensive compatibility for canonical names that were added after older
# copies of team_aliases.py were created.
LOCAL_ALIAS_FALLBACKS = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
    "Ginger FC": "Ginger FC 🏆🏆",
    "Ginger FC Trophy Trophy": "Ginger FC 🏆🏆",
    "Ginger FC 🏆🏆": "Ginger FC 🏆🏆",
}


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_first(paths: list[Path]) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def canon(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    value = _shared_canonical_team(value)
    return LOCAL_ALIAS_FALLBACKS.get(str(value).strip(), str(value).strip())


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    df = df.copy()
    for col in [
        "team", "opponent", "team_1", "team_2", "fantasy_team",
        "canonical_team", "canonical_opponent", "winner", "loser",
    ]:
        if col in df.columns:
            df[col] = df[col].map(canon)
    return df


def number(value, digits=2):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def integer(value):
    if pd.isna(value):
        return None
    return int(value)


def clean_optional_text(value):
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def clean_json_value(value):
    """Recursively make packet values deterministic and JSON-safe."""
    if isinstance(value, dict):
        return {key: clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if pd.isna(value) or not np.isfinite(float(value)):
            return None
        return round(float(value), 4)
    if pd.isna(value) if not isinstance(value, (str, bytes)) else False:
        return None
    return value


def historical_h2h(games, team, opponent, year, week):
    g = games[(games["team"] == team) & (games["opponent"] == opponent)].copy()
    g = g[(g["year"] < year) | ((g["year"] == year) & (g["week"] < week))]
    wins = int((g.result == "W").sum())
    losses = int((g.result == "L").sum())
    ties = int((g.result == "T").sum())
    return {
        "team": team,
        "opponent": opponent,
        "games": int(len(g)),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "record": f"{wins}-{losses}-{ties}",
        "points_for": number(g["points_for"].sum()) if "points_for" in g else None,
        "points_against": number(g["points_against"].sum()) if "points_against" in g else None,
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
        return {
            "available": False,
            "reason": "No validated weekly player rows were available for this week.",
            "top_starters": [],
            "position_leaders": [],
        }

    all_rows = lineups.copy()
    w = all_rows[
        (pd.to_numeric(all_rows["year"], errors="coerce") == year)
        & (pd.to_numeric(all_rows["week"], errors="coerce") == week)
    ].copy()

    if "is_starter" in w.columns:
        w = w[w["is_starter"].astype(str).str.lower().isin(["true", "1", "yes"])]

    w["fantasy_points"] = pd.to_numeric(w["fantasy_points"], errors="coerce")
    w = w[w["fantasy_points"].notna()].copy()

    if w.empty:
        return {
            "available": False,
            "reason": "Weekly lineup master contains no validated starters for this week.",
            "top_starters": [],
            "position_leaders": [],
        }

    valid_positions = {"QB", "RB", "WR", "TE", "K", "DEF"}

    def clean_position(value):
        if pd.isna(value):
            return None
        value = str(value).strip().upper()
        aliases = {
            "D/ST": "DEF",
            "DST": "DEF",
            "DEFENSE": "DEF",
        }
        value = aliases.get(value, value)
        return value if value in valid_positions else None

    # Prefer explicit current-row position fields. Yahoo/current collectors may
    # use different names, so check the common variants without assuming one.
    position_columns = [
        c for c in [
            "position", "player_position", "primary_position",
            "eligible_position", "eligible_positions",
        ]
        if c in w.columns
    ]

    def row_position(row):
        for col in position_columns:
            value = row.get(col)
            if pd.isna(value):
                continue
            # Eligible-position fields can contain values such as "WR,RB,W/R/T".
            for token in str(value).replace("|", ",").replace("/", ",").split(","):
                position = clean_position(token)
                if position:
                    return position
        return None

    w["_news_position"] = w.apply(row_position, axis=1)

    # Historical validated rows are a safe fallback for players whose current
    # API row does not carry a usable position.
    historical_position = {}
    hist = all_rows[
        pd.to_numeric(all_rows["year"], errors="coerce") < year
    ].copy()
    if "player" in hist.columns:
        hist_position_columns = [
            c for c in [
                "position", "player_position", "primary_position",
                "eligible_position", "eligible_positions",
            ]
            if c in hist.columns
        ]
        for _, row in hist.iterrows():
            player = str(row.get("player", "")).strip()
            if not player or player in historical_position:
                continue
            for col in hist_position_columns:
                value = row.get(col)
                if pd.isna(value):
                    continue
                for token in str(value).replace("|", ",").replace("/", ",").split(","):
                    position = clean_position(token)
                    if position:
                        historical_position[player] = position
                        break
                if player in historical_position:
                    break

    missing = w["_news_position"].isna()
    if missing.any():
        w.loc[missing, "_news_position"] = (
            w.loc[missing, "player"].astype(str).map(historical_position)
        )

    def row_fact(row):
        return {
            "player": str(row.get("player", "")),
            "team": canon(row.get("fantasy_team", "")),
            "position": row.get("_news_position"),
            "points": number(row["fantasy_points"]),
        }

    top = w.sort_values("fantasy_points", ascending=False).head(8)
    top_starters = [row_fact(row) for _, row in top.iterrows()]

    position_leaders = []
    positioned = w[w["_news_position"].notna()].copy()
    for position, group in positioned.groupby("_news_position"):
        row = group.sort_values("fantasy_points", ascending=False).iloc[0]
        position_leaders.append(row_fact(row))

    return {
        "available": True,
        "top_starter": top_starters[0],
        "top_starters": top_starters,
        "position_leaders": sorted(
            position_leaders,
            key=lambda x: x["points"] if x["points"] is not None else -999,
            reverse=True,
        ),
    }


def bad_beat_facts(df, year, week):
    required = {
        "year", "week", "fantasy_team", "opponent", "score",
        "opponent_score", "expected_win_rate", "weekly_score_rank",
        "bad_beat", "severe_bad_beat", "brutal_bad_beat",
        "lucky_win", "severe_lucky_win",
    }
    if df.empty or not required.issubset(df.columns):
        return {
            "available": False,
            "reason": "Validated bad-beat analysis was not available.",
            "bad_beats": [],
            "lucky_wins": [],
        }

    w = df[
        (pd.to_numeric(df["year"], errors="coerce") == year)
        & (pd.to_numeric(df["week"], errors="coerce") == week)
    ].copy()

    if w.empty:
        return {
            "available": False,
            "reason": "Validated bad-beat analysis contains no rows for this week.",
            "bad_beats": [],
            "lucky_wins": [],
        }

    def flag(row, col):
        return bool(pd.to_numeric(pd.Series([row.get(col, 0)]), errors="coerce").fillna(0).iloc[0])

    def fact(row):
        return {
            "team": canon(row["fantasy_team"]),
            "opponent": canon(row["opponent"]),
            "score": number(row["score"]),
            "opponent_score": number(row["opponent_score"]),
            "margin": number(row.get("margin")),
            "weekly_score_rank": integer(row["weekly_score_rank"]),
            "expected_win_rate": number(row["expected_win_rate"], 4),
            "all_play_wins": integer(row.get("all_play_wins")),
            "all_play_losses": integer(row.get("all_play_losses")),
        }

    bad = []
    lucky = []
    for _, row in w.iterrows():
        if flag(row, "bad_beat"):
            item = fact(row)
            item["severity"] = (
                "brutal" if flag(row, "brutal_bad_beat")
                else "severe" if flag(row, "severe_bad_beat")
                else "bad_beat"
            )
            bad.append(item)

        if flag(row, "lucky_win"):
            item = fact(row)
            item["severity"] = "severe" if flag(row, "severe_lucky_win") else "lucky"
            lucky.append(item)

    bad.sort(key=lambda x: x["expected_win_rate"] or 0, reverse=True)
    lucky.sort(key=lambda x: x["expected_win_rate"] or 1)

    return {
        "available": True,
        "bad_beats": bad,
        "lucky_wins": lucky,
    }


def managerial_facts(df, year, week):
    required = {
        "year", "week", "fantasy_team", "opponent", "actual_score",
        "optimal_score", "points_left_on_bench", "lineup_efficiency_pct",
    }
    if df.empty or not required.issubset(df.columns):
        return {
            "available": False,
            "reason": "Validated lineup-efficiency analysis was not available.",
            "decisions": [],
        }

    w = df[
        (pd.to_numeric(df["year"], errors="coerce") == year)
        & (pd.to_numeric(df["week"], errors="coerce") == week)
    ].copy()

    if w.empty:
        return {
            "available": False,
            "reason": "Lineup-efficiency analysis contains no rows for this week.",
            "decisions": [],
        }

    for col in [
        "actual_score", "optimal_score", "points_left_on_bench",
        "lineup_efficiency_pct", "avoidable_start_count", "missed_start_count",
    ]:
        if col in w.columns:
            w[col] = pd.to_numeric(w[col], errors="coerce")

    w = w.sort_values(
        ["points_left_on_bench", "lineup_efficiency_pct"],
        ascending=[False, True],
    )

    decisions = []
    for _, row in w.iterrows():
        decisions.append({
            "team": canon(row["fantasy_team"]),
            "opponent": canon(row["opponent"]),
            "actual_score": number(row["actual_score"]),
            "optimal_score": number(row["optimal_score"]),
            "points_left_on_bench": number(row["points_left_on_bench"]),
            "lineup_efficiency_pct": number(row["lineup_efficiency_pct"]),
            "avoidable_start_count": integer(row.get("avoidable_start_count")),
            "missed_start_count": integer(row.get("missed_start_count")),
            "should_have_benched": clean_optional_text(
                row.get("should_have_benched")
            ),
            "should_have_started": clean_optional_text(
                row.get("should_have_started")
            ),
        })

    return {
        "available": True,
        "worst_decision_week": decisions[0] if decisions else None,
        "decisions": decisions,
    }


def record_and_milestone_facts(games, year, week):
    current = games[(games["year"] == year) & (games["week"] == week)].copy()
    prior = games[
        (games["year"] < year)
        | ((games["year"] == year) & (games["week"] < week))
    ].copy()

    result = {
        "records_broken": [],
        "records_tied": [],
        "near_records": [],
        "career_milestones": [],
    }

    if current.empty or prior.empty:
        return result

    # Single-game scoring records.
    prior_high = prior["points_for"].max()
    prior_low = prior["points_for"].min()

    for _, row in current.iterrows():
        score = float(row["points_for"])
        base = {
            "team": str(row["team"]),
            "opponent": str(row["opponent"]),
            "value": number(score),
        }

        if score > prior_high:
            result["records_broken"].append({
                **base, "record": "Highest Single-Game Score",
                "previous_record": number(prior_high),
            })
        elif np.isclose(score, prior_high):
            result["records_tied"].append({
                **base, "record": "Highest Single-Game Score",
                "record_value": number(prior_high),
            })
        elif prior_high - score <= 5:
            result["near_records"].append({
                **base, "record": "Highest Single-Game Score",
                "record_value": number(prior_high),
                "distance": number(prior_high - score),
            })

        if score < prior_low:
            result["records_broken"].append({
                **base, "record": "Lowest Single-Game Score",
                "previous_record": number(prior_low),
            })
        elif np.isclose(score, prior_low):
            result["records_tied"].append({
                **base, "record": "Lowest Single-Game Score",
                "record_value": number(prior_low),
            })
        elif score - prior_low <= 5:
            result["near_records"].append({
                **base, "record": "Lowest Single-Game Score",
                "record_value": number(prior_low),
                "distance": number(score - prior_low),
            })

    # Margin records use one winner row per historical matchup.
    prior_wins = prior[prior["result"].astype(str) == "W"].copy()
    current_wins = current[current["result"].astype(str) == "W"].copy()
    if not prior_wins.empty and not current_wins.empty:
        prior_wins["abs_margin"] = (
            pd.to_numeric(prior_wins["points_for"], errors="coerce")
            - pd.to_numeric(prior_wins["points_against"], errors="coerce")
        ).abs()
        current_wins["abs_margin"] = (
            pd.to_numeric(current_wins["points_for"], errors="coerce")
            - pd.to_numeric(current_wins["points_against"], errors="coerce")
        ).abs()

        widest = prior_wins["abs_margin"].max()
        narrowest = prior_wins["abs_margin"].min()

        for _, row in current_wins.iterrows():
            margin = float(row["abs_margin"])
            base = {
                "team": str(row["team"]),
                "opponent": str(row["opponent"]),
                "value": number(margin),
            }
            if margin > widest:
                result["records_broken"].append({
                    **base, "record": "Biggest Blowout Win",
                    "previous_record": number(widest),
                })
            elif np.isclose(margin, widest):
                result["records_tied"].append({
                    **base, "record": "Biggest Blowout Win",
                    "record_value": number(widest),
                })
            elif widest - margin <= 5:
                result["near_records"].append({
                    **base, "record": "Biggest Blowout Win",
                    "record_value": number(widest),
                    "distance": number(widest - margin),
                })

            if margin < narrowest:
                result["records_broken"].append({
                    **base, "record": "Narrowest Win",
                    "previous_record": number(narrowest),
                })
            elif np.isclose(margin, narrowest):
                result["records_tied"].append({
                    **base, "record": "Narrowest Win",
                    "record_value": number(narrowest),
                })
            elif margin - narrowest <= 1:
                result["near_records"].append({
                    **base, "record": "Narrowest Win",
                    "record_value": number(narrowest),
                    "distance": number(margin - narrowest),
                })

    # Career milestone crossings caused by this week's games.
    milestones = {
        "wins": [25, 50, 75, 100],
        "losses": [25, 50, 75, 100],
        "points": [5000, 10000, 15000, 20000],
    }
    for team in sorted(current["team"].dropna().astype(str).unique()):
        before = prior[prior["team"] == team]
        now = current[current["team"] == team]

        before_wins = int((before["result"].astype(str) == "W").sum())
        after_wins = before_wins + int((now["result"].astype(str) == "W").sum())
        before_losses = int((before["result"].astype(str) == "L").sum())
        after_losses = before_losses + int((now["result"].astype(str) == "L").sum())
        before_points = float(pd.to_numeric(before["points_for"], errors="coerce").sum())
        after_points = before_points + float(pd.to_numeric(now["points_for"], errors="coerce").sum())

        for label, before_value, after_value, levels in [
            ("Career Wins", before_wins, after_wins, milestones["wins"]),
            ("Career Losses", before_losses, after_losses, milestones["losses"]),
            ("Career Points", before_points, after_points, milestones["points"]),
        ]:
            for level in levels:
                if before_value < level <= after_value:
                    result["career_milestones"].append({
                        "team": team,
                        "milestone": label,
                        "threshold": level,
                        "current": number(after_value),
                    })

    return result



def recent_transaction_facts(transactions, lineups, year, week):
    """
    Return transaction facts knowable through the end of the requested fantasy week.

    Editorial weeks run Tuesday 12:00 AM ET through Monday 11:59:59 PM ET.
    Week 1 is anchored to the first Tuesday in September for the season.
    """
    empty = {
        "available": False,
        "as_of": None,
        "as_of_et": None,
        "transactions": [],
        "team_transactions": {},
    }

    if transactions.empty:
        return {
            **empty,
            "reason": "No normalized current-season transaction file was available.",
        }

    required = {"year", "team", "transaction_type"}
    if not required.issubset(transactions.columns):
        return {
            **empty,
            "reason": "Normalized transaction data is missing required columns.",
        }

    t = transactions.copy()
    t["year"] = pd.to_numeric(t["year"], errors="coerce")
    t = t[t["year"] == year].copy()

    if t.empty:
        return {
            **empty,
            "reason": f"No normalized transactions were available for {year}.",
        }

    if "timestamp" in t.columns:
        t["_transaction_time"] = pd.to_datetime(
            pd.to_numeric(t["timestamp"], errors="coerce"),
            unit="s",
            utc=True,
            errors="coerce",
        )
    else:
        t["_transaction_time"] = pd.NaT

    if "date" in t.columns:
        date_time = pd.to_datetime(t["date"], utc=True, errors="coerce")
        t["_transaction_time"] = t["_transaction_time"].fillna(date_time)

    # Deterministic fantasy/editorial week boundary:
    # Tuesday 12:00 AM ET through Monday 11:59:59 PM ET.
    september_first = pd.Timestamp(
        year=year, month=9, day=1, tz="America/New_York"
    )
    days_until_tuesday = (1 - september_first.weekday()) % 7
    week1_start_et = september_first + pd.Timedelta(days=days_until_tuesday)

    week_start_et = week1_start_et + pd.Timedelta(weeks=week - 1)
    cutoff_et = (
        week_start_et
        + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)
    )
    cutoff = cutoff_et.tz_convert("UTC")

    t = t[
        t["_transaction_time"].notna()
        & (t["_transaction_time"] <= cutoff)
    ].copy()

    if t.empty:
        return {
            "available": True,
            "as_of": cutoff.isoformat(),
            "as_of_et": cutoff_et.isoformat(),
            "transactions": [],
            "team_transactions": {},
        }

    t["team"] = t["team"].map(canon)

    sort_cols = ["_transaction_time"]
    if "transaction_id" in t.columns:
        sort_cols.append("transaction_id")
    t = t.sort_values(sort_cols)

    facts = []
    for _, row in t.iterrows():
        facts.append({
            "transaction_id": integer(row.get("transaction_id")),
            "date": row["_transaction_time"].isoformat(),
            "team": canon(row.get("team")),
            "transaction_type": clean_optional_text(row.get("transaction_type")),
            "added_player": clean_optional_text(row.get("added_player")),
            "acquisition_type": clean_optional_text(row.get("acquisition_type")),
            "dropped_player": clean_optional_text(row.get("dropped_player")),
        })

    by_team = {}
    for fact in facts:
        by_team.setdefault(fact["team"], []).append(fact)

    return {
        "available": True,
        "as_of": cutoff.isoformat(),
        "as_of_et": cutoff_et.isoformat(),
        "transactions": facts,
        "team_transactions": by_team,
    }

def future_matchup_facts(matchups, games, year, completed_week):
    next_week = completed_week + 1
    if matchups.empty:
        return {
            "available": False,
            "week": next_week,
            "reason": "Authoritative upcoming-matchup file was unavailable.",
            "matchups": [],
        }

    m = matchups.copy()
    for col in ["year", "week"]:
        if col in m.columns:
            m[col] = pd.to_numeric(m[col], errors="coerce")

    future = m[(m["year"] == year) & (m["week"] == next_week)].copy()
    if future.empty or not {"team_1", "team_2"}.issubset(future.columns):
        return {
            "available": False,
            "week": next_week,
            "reason": "No authoritative next-week matchup rows are present in the upcoming-matchup file yet.",
            "matchups": [],
        }

    rows = []
    seen = set()
    for _, row in future.iterrows():
        a, b = canon(row["team_1"]), canon(row["team_2"])
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        item = {
            "team_1": a,
            "team_2": b,
            "historical_h2h_before_matchup": historical_h2h(
                games, a, b, year, next_week
            ),
        }
        for src, dst in [
            ("projected_1", "team_1_projection"),
            ("projected_2", "team_2_projection"),
            ("team_1_projected", "team_1_projection"),
            ("team_2_projected", "team_2_projection"),
        ]:
            if src in row.index and pd.notna(row[src]) and dst not in item:
                item[dst] = number(row[src])
        rows.append(item)

    return {
        "available": len(rows) > 0,
        "week": next_week,
        "matchups": rows,
    }


def main():
    matchups = normalize(load(MATCHUPS))
    if matchups.empty:
        raise RuntimeError("Canonical matchup master is missing or empty.")

    state = detect_latest_completed_week(matchups)
    week = int(state.latest_completed_week or 0)
    if week == 0:
        print(
            f"PASS — no completed {CURRENT_SEASON} week; "
            "no weekly news context generated."
        )
        return

    games = normalize(load(TEAM_GAMES))
    if games.empty:
        raise RuntimeError("data/history/team_games.csv is missing or empty.")

    for col in ["year", "week", "points_for", "points_against"]:
        games[col] = pd.to_numeric(games[col], errors="coerce")

    wg = games[
        (games["year"] == CURRENT_SEASON)
        & (games["week"] == week)
    ].copy()

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
        winner, loser = (
            (row, other)
            if row["points_for"] >= other["points_for"]
            else (other, row)
        )

        stories.append({
            "winner": str(winner["team"]),
            "loser": str(loser["team"]),
            "winner_score": number(winner["points_for"]),
            "loser_score": number(loser["points_for"]),
            "margin": number(
                abs(float(winner["points_for"]) - float(loser["points_for"]))
            ),
            "historical_h2h_before_game": historical_h2h(
                games,
                str(winner["team"]),
                str(loser["team"]),
                CURRENT_SEASON,
                week,
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

        run = prior_streak(
            games, str(row["team"]), opposite, CURRENT_SEASON, week
        )
        if run >= 2:
            snapped.append({
                "team": str(row["team"]),
                "streak_type": "losing" if opposite == "L" else "winning",
                "length": run,
            })

    standings = normalize(load(STANDINGS))
    standings_rows = []
    if not standings.empty and "year" in standings.columns:
        s = standings[
            pd.to_numeric(standings["year"], errors="coerce") == CURRENT_SEASON
        ]
        standings_rows = s.to_dict("records")

    season_records = normalize(load(SEASON_RECORDS))
    season_rows = []
    if not season_records.empty and "year" in season_records.columns:
        s = season_records[
            pd.to_numeric(season_records["year"], errors="coerce")
            == CURRENT_SEASON
        ]
        keep = [
            c for c in [
                "team", "wins", "losses", "ties", "points_for",
                "points_against", "point_diff", "win_pct",
            ]
            if c in s.columns
        ]
        season_rows = s[keep].to_dict("records")

    lineups = normalize(load_first(WEEKLY_LINEUP_CANDIDATES))
    bad_beats = normalize(load(BAD_BEATS))
    efficiency = normalize(load(LINEUP_EFFICIENCY))
    upcoming_matchups = normalize(load(UPCOMING_MATCHUPS))
    transactions = normalize(load(TRANSACTIONS))

    packet = {
        "schema_version": 4,
        "season": CURRENT_SEASON,
        "week": week,
        "editorial_guardrail": (
            "AI may add satire, but factual claims must be supported by this packet. "
            "Predictions and opinions must be clearly labeled."
        ),
        "week_summary": {
            "highest_scoring_team": {
                "team": str(high["team"]),
                "points": number(high["points_for"]),
            },
            "lowest_scoring_team": {
                "team": str(low["team"]),
                "points": number(low["points_for"]),
            },
            "closest_game": min(stories, key=lambda x: x["margin"]),
            "biggest_blowout": max(stories, key=lambda x: x["margin"]),
        },
        "matchups": sorted(stories, key=lambda x: x["margin"]),
        "player_facts": player_facts(lineups, CURRENT_SEASON, week),
        "bad_beats": bad_beat_facts(bad_beats, CURRENT_SEASON, week),
        "managerial_decisions": managerial_facts(
            efficiency, CURRENT_SEASON, week
        ),
        "recent_transactions": recent_transaction_facts(
            transactions, lineups, CURRENT_SEASON, week
        ),
        "streaks_snapped": snapped,
        "records_and_milestones": record_and_milestone_facts(
            games, CURRENT_SEASON, week
        ),
        "standings": standings_rows,
        "season_team_context": season_rows,
        "future_matchups": future_matchup_facts(
            upcoming_matchups, games, CURRENT_SEASON, week
        ),
        "planned_adapters": {
            "power_rankings": (
                "Phase 2: deterministic 1-12 ranking model using results, "
                "scoring, all-play/luck, lineup quality, and recent form."
            ),
        },
    }

    packet = clean_json_value(packet)

    # Schema-v4 guardrails: fail the build rather than hand ambiguous or dirty
    # facts to the article writer.
    if packet["schema_version"] != 4:
        raise RuntimeError("Weekly news packet schema version is not 4.")

    for story in packet["matchups"]:
        h2h = story["historical_h2h_before_game"]
        if h2h.get("team") != story["winner"] or h2h.get("opponent") != story["loser"]:
            raise RuntimeError("Completed-game H2H orientation is ambiguous.")

    future = packet["future_matchups"]
    if future.get("available"):
        if len(future.get("matchups", [])) != 6:
            raise RuntimeError(
                f"Expected 6 future matchups; found {len(future.get('matchups', []))}."
            )
        future_teams = []
        for item in future["matchups"]:
            future_teams.extend([item["team_1"], item["team_2"]])
            h2h = item["historical_h2h_before_matchup"]
            if h2h.get("team") != item["team_1"] or h2h.get("opponent") != item["team_2"]:
                raise RuntimeError("Future-matchup H2H orientation is ambiguous.")
        if len(future_teams) != 12 or len(set(future_teams)) != 12:
            raise RuntimeError("Future matchup packet does not contain 12 unique teams.")

    decisions = packet["managerial_decisions"].get("decisions", [])
    for item in decisions:
        for field in ["should_have_benched", "should_have_started"]:
            if isinstance(item.get(field), str) and item[field].strip().lower() == "nan":
                raise RuntimeError(f"Managerial field {field} contains string 'nan'.")

    transaction_section = packet["recent_transactions"]
    if transaction_section.get("available"):
        as_of = pd.to_datetime(transaction_section.get("as_of"), utc=True, errors="coerce")
        for item in transaction_section.get("transactions", []):
            tx_time = pd.to_datetime(item.get("date"), utc=True, errors="coerce")
            if pd.isna(tx_time) or pd.isna(as_of) or tx_time > as_of:
                raise RuntimeError(
                    "Recent transaction packet contains a transaction beyond its as-of cutoff."
                )

    player_section = packet["player_facts"]
    if player_section.get("available"):
        for item in player_section.get("top_starters", []):
            if item.get("position") is not None and item["position"] not in {
                "QB", "RB", "WR", "TE", "K", "DEF"
            }:
                raise RuntimeError(
                    f"Unexpected player position in news packet: {item['position']}"
                )

    NEWS.mkdir(parents=True, exist_ok=True)
    out = NEWS / f"week_{week:02d}_context.json"
    out.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    print(f"PASS — Weekly News Intelligence: {CURRENT_SEASON} Week {week}")
    print("PASS — schema v4 packet validation")
    print("PASS — 6 matchup stories / 12 teams validated")
    print(
        "PASS — bad beats: "
        f"{'available' if packet['bad_beats']['available'] else 'not available'}"
    )
    print(
        "PASS — managerial decisions: "
        f"{'available' if packet['managerial_decisions']['available'] else 'not available'}"
    )
    print(
        "PASS — player facts: "
        f"{'available' if packet['player_facts']['available'] else 'not available'}"
    )
    print(
        "PASS — recent transactions: "
        f"{len(packet['recent_transactions'].get('transactions', []))} "
        f"through {packet['recent_transactions'].get('as_of_et') or packet['recent_transactions'].get('as_of') or 'safe cutoff unavailable'}"
    )
    print(
        "PASS — future matchups: "
        f"{'available' if packet['future_matchups']['available'] else 'not available'}"
    )
    print(
        "PASS — records/milestones: "
        f"{len(packet['records_and_milestones']['records_broken'])} broken, "
        f"{len(packet['records_and_milestones']['records_tied'])} tied, "
        f"{len(packet['records_and_milestones']['near_records'])} near, "
        f"{len(packet['records_and_milestones']['career_milestones'])} milestones"
    )
    print(f"PASS — wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()