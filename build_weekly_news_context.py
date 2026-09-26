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


# ============================================================
# WEEKLY STORY ENGINE
# ============================================================

def special_teams_facts(lineups, games, year, week):
    """
    Find noteworthy kicker and defense performances.

    These are deterministic fantasy-data facts.  The detector
    emphasizes performances that were large relative to the
    team's score or the matchup margin.
    """

    if lineups.empty:
        return []

    df = normalize(lineups)

    required = {
        "year",
        "week",
        "fantasy_team",
        "player",
        "lineup_slot",
        "fantasy_points",
        "is_starter",
    }

    if not required.issubset(df.columns):
        return []

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df["fantasy_points"] = pd.to_numeric(
        df["fantasy_points"],
        errors="coerce",
    ).fillna(0.0)

    wk = df[
        df["year"].eq(year)
        & df["week"].eq(week)
    ].copy()

    if wk.empty:
        return []

    # Handle bools that may have been serialized as strings.
    wk["_starter"] = (
        wk["is_starter"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    wk = wk[wk["_starter"]].copy()

    wk["lineup_slot"] = (
        wk["lineup_slot"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace({
            "DST": "DEF",
            "D/ST": "DEF",
        })
    )

    wk = wk[
        wk["lineup_slot"].isin({"K", "DEF"})
    ].copy()

    if wk.empty:
        return []

    game_df = normalize(games)

    if not game_df.empty:
        for col in [
            "year",
            "week",
            "team_1_score",
            "team_2_score",
            "margin",
        ]:
            if col in game_df.columns:
                game_df[col] = pd.to_numeric(
                    game_df[col],
                    errors="coerce",
                )

        game_df = game_df[
            game_df["year"].eq(year)
            & game_df["week"].eq(week)
        ].copy()

    facts = []

    for _, row in wk.iterrows():

        team = row["fantasy_team"]
        points = float(row["fantasy_points"])

        team_score = pd.to_numeric(
            row.get("team_score"),
            errors="coerce",
        )

        opponent = row.get("opponent")
        margin = None
        won = None

        if not game_df.empty:
            match = game_df[
                game_df["team_1"].eq(team)
                | game_df["team_2"].eq(team)
            ]

            if not match.empty:
                game = match.iloc[0]

                if game["team_1"] == team:
                    team_score = game["team_1_score"]
                    opponent = game["team_2"]
                    opp_score = game["team_2_score"]
                else:
                    team_score = game["team_2_score"]
                    opponent = game["team_1"]
                    opp_score = game["team_1_score"]

                if pd.notna(team_score) and pd.notna(opp_score):
                    margin = abs(
                        float(team_score)
                        - float(opp_score)
                    )
                    won = float(team_score) > float(opp_score)

        share = None

        if pd.notna(team_score) and float(team_score) != 0:
            share = (
                points / float(team_score) * 100.0
            )

        # Only surface legitimately interesting special-team
        # performances.
        notable = (
            points >= 15
            or (
                margin is not None
                and won
                and points > margin
            )
            or (
                share is not None
                and share >= 15
            )
        )

        if not notable:
            continue

        importance = 5.0

        if points >= 20:
            importance += 2.0
        elif points >= 15:
            importance += 1.0

        if (
            margin is not None
            and won
            and points > margin
        ):
            importance += 1.5

        if share is not None and share >= 15:
            importance += 0.5

        slot = row["lineup_slot"]

        facts.append({
            "category": (
                "kicker_impact"
                if slot == "K"
                else "defense_impact"
            ),
            "importance": round(
                min(10.0, importance),
                2,
            ),
            "evidence_type": "derived_fact",
            "team": team,
            "opponent": opponent,
            "player": row["player"],
            "position": slot,
            "points": number(points),
            "team_score": number(team_score),
            "share_of_team_score_pct": (
                number(share)
                if share is not None
                else None
            ),
            "matchup_margin": (
                number(margin)
                if margin is not None
                else None
            ),
            "team_won": won,
            "headline_fact": (
                f"{row['player']} scored {points:.2f} "
                f"points at {slot} for {team}"
                + (
                    f", accounting for {share:.1f}% "
                    f"of the team's score"
                    if share is not None
                    else ""
                )
                + (
                    f" in a game decided by "
                    f"{margin:.2f} points."
                    if margin is not None
                    else "."
                )
            ),
        })

    return sorted(
        facts,
        key=lambda x: x["importance"],
        reverse=True,
    )


def acquisition_impact_facts(
    transactions,
    lineups,
    year,
    week,
):
    """
    Connect recent additions to same-week fantasy production.

    This does not claim the transaction caused the win/loss.
    It only records the acquisition and subsequent production.
    """

    if transactions.empty or lineups.empty:
        return []

    tx = normalize(transactions)
    lu = normalize(lineups)

    required_tx = {
        "year",
        "team",
        "added_player",
    }

    required_lu = {
        "year",
        "week",
        "fantasy_team",
        "player",
        "fantasy_points",
        "is_starter",
    }

    if (
        not required_tx.issubset(tx.columns)
        or not required_lu.issubset(lu.columns)
    ):
        return []

    tx["year"] = pd.to_numeric(
        tx["year"],
        errors="coerce",
    )

    lu["year"] = pd.to_numeric(
        lu["year"],
        errors="coerce",
    )

    lu["week"] = pd.to_numeric(
        lu["week"],
        errors="coerce",
    )

    lu["fantasy_points"] = pd.to_numeric(
        lu["fantasy_points"],
        errors="coerce",
    ).fillna(0.0)

    tx = tx[tx["year"].eq(year)].copy()

    wk = lu[
        lu["year"].eq(year)
        & lu["week"].eq(week)
    ].copy()

    if tx.empty or wk.empty:
        return []

    if "date" in tx.columns:
        tx["_date"] = pd.to_datetime(
            tx["date"],
            errors="coerce",
            utc=True,
        )
    elif "timestamp" in tx.columns:
        tx["_date"] = pd.to_datetime(
            tx["timestamp"],
            errors="coerce",
            utc=True,
        )
    else:
        tx["_date"] = pd.NaT

    # Enforce the same editorial as-of boundary used by recent_transaction_facts.
    # This prevents future-week acquisitions from leaking into an earlier story desk.
    september_first = pd.Timestamp(year=year, month=9, day=1, tz="America/New_York")
    days_until_tuesday = (1 - september_first.weekday()) % 7
    week1_start_et = september_first + pd.Timedelta(days=days_until_tuesday)
    week_start_et = week1_start_et + pd.Timedelta(weeks=week - 1)
    cutoff_et = week_start_et + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)
    cutoff = cutoff_et.tz_convert("UTC")
    tx = tx[tx["_date"].notna() & tx["_date"].le(cutoff)].copy()
    if tx.empty:
        return []

    wk["_starter"] = (
        wk["is_starter"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    facts = []

    for _, move in tx.iterrows():

        player = clean_optional_text(
            move.get("added_player")
        )

        team = clean_optional_text(
            move.get("team")
        )

        if not player or not team:
            continue

        match = wk[
            wk["fantasy_team"].eq(team)
            & wk["player"].eq(player)
        ]

        if match.empty:
            continue

        player_week = match.iloc[0]

        points = float(
            player_week["fantasy_points"]
        )

        started = bool(
            player_week["_starter"]
        )

        # Keep only additions that actually produced something
        # noteworthy that week.
        if started:
            if points < 10:
                continue
        else:
            if points < 15:
                continue

        importance = 5.0

        if started:
            importance += 1.0

        if points >= 20:
            importance += 2.0
        elif points >= 15:
            importance += 1.0

        acquisition_type = clean_optional_text(
            move.get("acquisition_type")
        )

        facts.append({
            "category": (
                "acquisition_hero"
                if started
                else "acquisition_bench_explosion"
            ),
            "importance": round(
                min(10.0, importance),
                2,
            ),
            "evidence_type": "fact",
            "team": team,
            "player": player,
            "points": number(points),
            "started": started,
            "lineup_slot": clean_optional_text(
                player_week.get("lineup_slot")
            ),
            "acquisition_type": acquisition_type,
            "transaction_date": (
                move["_date"].isoformat()
                if pd.notna(move["_date"])
                else None
            ),
            "dropped_player": clean_optional_text(
                move.get("dropped_player")
            ),
            "headline_fact": (
                f"{team} recently acquired {player}"
                + (
                    f" via {acquisition_type}"
                    if acquisition_type
                    else ""
                )
                + (
                    f" and started him for "
                    f"{points:.2f} points."
                    if started
                    else
                    f", but his {points:.2f}-point "
                    f"performance remained on the bench."
                )
            ),
        })

    # Avoid duplicate player/team facts if a transaction feed
    # contains multiple related rows.
    deduped = {}

    for fact in facts:
        key = (
            fact["team"],
            fact["player"],
            fact["category"],
        )

        current = deduped.get(key)

        if (
            current is None
            or fact["importance"]
            > current["importance"]
        ):
            deduped[key] = fact

    return sorted(
        deduped.values(),
        key=lambda x: x["importance"],
        reverse=True,
    )


def lineup_anomaly_facts(
    lineups,
    bench_decisions,
    year,
    week,
):
    """
    Find unusual scoring distributions and lineup events.
    """

    if lineups.empty:
        return []

    df = normalize(lineups)

    required = {
        "year",
        "week",
        "fantasy_team",
        "player",
        "fantasy_points",
        "is_starter",
        "is_bench",
    }

    if not required.issubset(df.columns):
        return []

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df["week"] = pd.to_numeric(
        df["week"],
        errors="coerce",
    )

    df["fantasy_points"] = pd.to_numeric(
        df["fantasy_points"],
        errors="coerce",
    ).fillna(0.0)

    wk = df[
        df["year"].eq(year)
        & df["week"].eq(week)
    ].copy()

    if wk.empty:
        return []

    wk["_starter"] = (
        wk["is_starter"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    wk["_bench"] = (
        wk["is_bench"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    facts = []

    # --------------------------------------------------------
    # Individual starter/bench anomalies
    # --------------------------------------------------------

    starters = wk[wk["_starter"]].copy()
    bench = wk[wk["_bench"]].copy()

    for _, row in bench[
        bench["fantasy_points"].ge(20)
    ].iterrows():

        points = float(row["fantasy_points"])

        facts.append({
            "category": "bench_explosion",
            "importance": round(
                min(10.0, 6.0 + points / 20.0),
                2,
            ),
            "evidence_type": "fact",
            "team": row["fantasy_team"],
            "player": row["player"],
            "points": number(points),
            "headline_fact": (
                f"{row['fantasy_team']} had "
                f"{row['player']}'s {points:.2f} "
                f"points on the bench."
            ),
        })

    for _, row in starters[
        starters["fantasy_points"].le(1)
    ].iterrows():

        points = float(row["fantasy_points"])

        facts.append({
            "category": "starter_dud",
            "importance": 5.5,
            "evidence_type": "fact",
            "team": row["fantasy_team"],
            "player": row["player"],
            "points": number(points),
            "headline_fact": (
                f"{row['fantasy_team']} started "
                f"{row['player']}, who scored only "
                f"{points:.2f} points."
            ),
        })

    # --------------------------------------------------------
    # One-player carry jobs
    # --------------------------------------------------------

    for team, group in starters.groupby(
        "fantasy_team"
    ):

        if group.empty:
            continue

        team_score = pd.to_numeric(
            group["team_score"],
            errors="coerce",
        ).dropna()

        if team_score.empty:
            total = group["fantasy_points"].sum()
        else:
            total = float(team_score.iloc[0])

        if not total:
            continue

        top = group.sort_values(
            "fantasy_points",
            ascending=False,
        ).iloc[0]

        top_points = float(top["fantasy_points"])
        share = top_points / total * 100.0

        # Ordinary star performances should not crowd the story desk.
        # 30-35% is mildly notable, 35-40% strong, 40%+ major.
        if share >= 30:
            if share >= 40:
                carry_importance = 9.0 + min(1.0, (share - 40.0) / 10.0)
            elif share >= 35:
                carry_importance = 7.5 + (share - 35.0) * 0.30
            else:
                carry_importance = 6.0 + (share - 30.0) * 0.30

            facts.append({
                "category": "one_player_carry",
                "importance": round(min(10.0, carry_importance), 2),
                "evidence_type": "derived_fact",
                "team": team,
                "player": top["player"],
                "points": number(top_points),
                "team_score": number(total),
                "share_of_team_score_pct": number(
                    share
                ),
                "headline_fact": (
                    f"{top['player']} supplied "
                    f"{share:.1f}% of {team}'s "
                    f"entire score."
                ),
            })

    # --------------------------------------------------------
    # Existing validated managerial analysis, when available
    # --------------------------------------------------------

    if not bench_decisions.empty:

        bd = normalize(bench_decisions)

        if {"year", "week"}.issubset(bd.columns):

            bd["year"] = pd.to_numeric(
                bd["year"],
                errors="coerce",
            )

            bd["week"] = pd.to_numeric(
                bd["week"],
                errors="coerce",
            )

            current = bd[
                bd["year"].eq(year)
                & bd["week"].eq(week)
            ].copy()

            if not current.empty:

                for col in [
                    "points_left_on_bench",
                    "optimization_gain",
                    "loss_margin",
                ]:
                    if col in current.columns:
                        current[col] = pd.to_numeric(
                            current[col],
                            errors="coerce",
                        )

                if "manager_caused_loss" in current.columns:
                    caused = current[
                        current["manager_caused_loss"]
                        .astype(str)
                        .str.lower()
                        .isin({"true", "1", "yes"})
                    ]

                    for _, row in caused.iterrows():

                        team = row.get(
                            "canonical_team",
                            row.get("fantasy_team"),
                        )

                        gain = row.get(
                            "optimization_gain"
                        )

                        facts.append({
                            "category":
                                "manager_caused_loss",
                            "importance": 9.0,
                            "evidence_type":
                                "derived_fact",
                            "team": team,
                            "opponent": row.get(
                                "canonical_opponent",
                                row.get("opponent"),
                            ),
                            "optimization_gain":
                                number(gain),
                            "should_have_started":
                                clean_optional_text(
                                    row.get(
                                        "should_have_started"
                                    )
                                ),
                            "should_have_benched":
                                clean_optional_text(
                                    row.get(
                                        "should_have_benched"
                                    )
                                ),
                            "headline_fact": (
                                f"{team} had a validated "
                                f"manager-caused loss"
                                + (
                                    f" with {float(gain):.2f} "
                                    f"points of available "
                                    f"optimization."
                                    if pd.notna(gain)
                                    else "."
                                )
                            ),
                        })

    return sorted(
        facts,
        key=lambda x: x["importance"],
        reverse=True,
    )


def historical_rarity_facts(games, year, week):
    """
    Compare this week's completed games with prior league history.

    This intentionally focuses on facts that can be proven from
    the canonical matchup history.
    """

    if games.empty:
        return []

    df = normalize(games)

    required = {
        "year",
        "week",
        "team_1",
        "team_2",
        "team_1_score",
        "team_2_score",
    }

    if not required.issubset(df.columns):
        return []

    for col in [
        "year",
        "week",
        "team_1_score",
        "team_2_score",
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    current = df[
        df["year"].eq(year)
        & df["week"].eq(week)
    ].copy()

    prior = df[
        (df["year"] < year)
        | (
            df["year"].eq(year)
            & df["week"].lt(week)
        )
    ].copy()

    if current.empty:
        return []

    # Convert historical matchups to team-game rows.
    historical_scores = []

    for _, game in prior.iterrows():
        for team_col, score_col, opp_col, opp_score_col in [
            (
                "team_1",
                "team_1_score",
                "team_2",
                "team_2_score",
            ),
            (
                "team_2",
                "team_2_score",
                "team_1",
                "team_1_score",
            ),
        ]:
            score = game.get(score_col)
            opp_score = game.get(opp_score_col)

            if pd.isna(score) or pd.isna(opp_score):
                continue

            historical_scores.append({
                "team": game.get(team_col),
                "score": float(score),
                "opponent": game.get(opp_col),
                "opponent_score": float(opp_score),
                "won": float(score) > float(opp_score),
                "lost": float(score) < float(opp_score),
            })

    hist = pd.DataFrame(historical_scores)

    facts = []

    for _, game in current.iterrows():

        for team_col, score_col, opp_col, opp_score_col in [
            (
                "team_1",
                "team_1_score",
                "team_2",
                "team_2_score",
            ),
            (
                "team_2",
                "team_2_score",
                "team_1",
                "team_1_score",
            ),
        ]:

            team = game[team_col]
            opponent = game[opp_col]
            score = float(game[score_col])
            opp_score = float(game[opp_score_col])

            won = score > opp_score
            lost = score < opp_score

            if hist.empty:
                continue

            if lost:
                higher_losing_scores = hist[
                    hist["lost"]
                    & hist["score"].gt(score)
                ]

                losing_scores = hist[
                    hist["lost"]
                ]

                rank = (
                    len(higher_losing_scores) + 1
                )

                if rank <= 10:
                    facts.append({
                        "category":
                            "historically_high_losing_score",
                        "importance": round(
                            9.0
                            if rank <= 3
                            else 8.0
                            if rank <= 5
                            else 7.0,
                            2,
                        ),
                        "evidence_type":
                            "historical_fact",
                        "team": team,
                        "opponent": opponent,
                        "score": number(score),
                        "opponent_score":
                            number(opp_score),
                        "historical_rank": rank,
                        "historical_sample":
                            len(losing_scores),
                        "headline_fact": (
                            f"{team}'s {score:.2f}-point "
                            f"loss ranks #{rank} among "
                            f"the highest losing scores "
                            f"before this week."
                        ),
                    })

            if won:
                lower_winning_scores = hist[
                    hist["won"]
                    & hist["score"].lt(score)
                ]

                winning_scores = hist[
                    hist["won"]
                ]

                rank = (
                    len(lower_winning_scores) + 1
                )

                if rank <= 10:
                    facts.append({
                        "category":
                            "historically_low_winning_score",
                        "importance": round(
                            8.5
                            if rank <= 3
                            else 7.5
                            if rank <= 5
                            else 6.5,
                            2,
                        ),
                        "evidence_type":
                            "historical_fact",
                        "team": team,
                        "opponent": opponent,
                        "score": number(score),
                        "opponent_score":
                            number(opp_score),
                        "historical_rank": rank,
                        "historical_sample":
                            len(winning_scores),
                        "headline_fact": (
                            f"{team}'s {score:.2f}-point "
                            f"win ranks #{rank} among "
                            f"the lowest winning scores "
                            f"before this week."
                        ),
                    })

    return sorted(
        facts,
        key=lambda x: x["importance"],
        reverse=True,
    )


def compound_story_facts(
    lineups,
    bench_decisions,
    games,
    special_teams,
    acquisitions,
    anomalies,
    year,
    week,
):
    """Synthesize related deterministic facts into editorially useful stories."""
    facts = []

    # Canonical matchup lookup, one row per team.
    matchup_by_team = {}
    g = normalize(games)
    if not g.empty and {"year", "week", "team_1", "team_2", "team_1_score", "team_2_score"}.issubset(g.columns):
        for col in ["year", "week", "team_1_score", "team_2_score"]:
            g[col] = pd.to_numeric(g[col], errors="coerce")
        current_games = g[g["year"].eq(year) & g["week"].eq(week)].copy()
        for _, row in current_games.iterrows():
            a, b = row["team_1"], row["team_2"]
            sa, sb = float(row["team_1_score"]), float(row["team_2_score"])
            matchup_by_team[a] = {"opponent": b, "score": sa, "opponent_score": sb, "margin": abs(sa-sb), "won": sa > sb, "lost": sa < sb}
            matchup_by_team[b] = {"opponent": a, "score": sb, "opponent_score": sa, "margin": abs(sa-sb), "won": sb > sa, "lost": sb < sa}

    # Manager-caused losses / multiple mistakes. Use validated optimization output.
    bd = normalize(bench_decisions)
    if not bd.empty and {"year", "week", "fantasy_team"}.issubset(bd.columns):
        bd["year"] = pd.to_numeric(bd["year"], errors="coerce")
        bd["week"] = pd.to_numeric(bd["week"], errors="coerce")
        current = bd[bd["year"].eq(year) & bd["week"].eq(week)].copy()
        for _, row in current.iterrows():
            team = canon(row.get("canonical_team", row.get("fantasy_team")))
            game = matchup_by_team.get(team)
            if not game:
                continue
            gain = pd.to_numeric(row.get("optimization_gain"), errors="coerce")
            if pd.isna(gain):
                actual = pd.to_numeric(row.get("actual_score"), errors="coerce")
                optimal = pd.to_numeric(row.get("optimal_score"), errors="coerce")
                gain = optimal - actual if pd.notna(actual) and pd.notna(optimal) else np.nan
            left = pd.to_numeric(row.get("points_left_on_bench"), errors="coerce")
            avoidable = pd.to_numeric(row.get("avoidable_start_count"), errors="coerce")
            missed = pd.to_numeric(row.get("missed_start_count"), errors="coerce")
            caused_flag = str(row.get("manager_caused_loss", "")).strip().lower() in {"true", "1", "yes"}
            reversed_result = bool(game["lost"] and pd.notna(gain) and float(gain) > float(game["margin"]))

            if caused_flag or reversed_result:
                would_win_by = float(gain) - float(game["margin"]) if pd.notna(gain) else None
                facts.append({
                    "category": "manager_blew_game",
                    "importance": round(min(10.0, 9.0 + min(1.0, max(0.0, (would_win_by or 0) / 15.0))), 2),
                    "evidence_type": "compound_derived_fact",
                    "team": team,
                    "opponent": game["opponent"],
                    "loss_margin": number(game["margin"]),
                    "optimization_gain": number(gain),
                    "points_left_on_bench": number(left),
                    "would_have_won_by": number(would_win_by),
                    "avoidable_start_count": integer(avoidable),
                    "missed_start_count": integer(missed),
                    "should_have_started": clean_optional_text(row.get("should_have_started")),
                    "should_have_benched": clean_optional_text(row.get("should_have_benched")),
                    "headline_fact": f"{team} lost to {game['opponent']} by {game['margin']:.2f} despite {float(gain):.2f} points of validated lineup optimization being available, enough to flip the result" + (f" into a {would_win_by:.2f}-point win." if would_win_by is not None else "."),
                    "suppresses": ["manager_caused_loss", "bench_explosion", "starter_dud"],
                })
            elif game["lost"] and pd.notna(left) and float(left) >= 20 and ((pd.notna(avoidable) and avoidable >= 2) or (pd.notna(missed) and missed >= 2)):
                facts.append({
                    "category": "multiple_managerial_mistakes",
                    "importance": round(min(8.5, 6.5 + float(left) / 25.0), 2),
                    "evidence_type": "compound_derived_fact",
                    "team": team,
                    "opponent": game["opponent"],
                    "loss_margin": number(game["margin"]),
                    "points_left_on_bench": number(left),
                    "avoidable_start_count": integer(avoidable),
                    "missed_start_count": integer(missed),
                    "headline_fact": f"{team} lost by {game['margin']:.2f} while leaving {float(left):.2f} points on the bench across multiple avoidable lineup decisions.",
                    "suppresses": ["bench_explosion", "starter_dud"],
                })

    # Combine K + DEF when their contribution mattered to a win.
    by_team = {}
    for item in special_teams:
        if item.get("position") in {"K", "DEF"}:
            by_team.setdefault(item.get("team"), {})[item.get("position")] = item
    for team, slots in by_team.items():
        if not {"K", "DEF"}.issubset(slots):
            continue
        game = matchup_by_team.get(team)
        if not game or not game["won"]:
            continue
        combined = float(slots["K"].get("points", 0)) + float(slots["DEF"].get("points", 0))
        if combined <= game["margin"] and combined < 20:
            continue
        leverage = combined / max(game["margin"], 0.5)
        importance = min(10.0, 7.0 + min(2.0, leverage / 4.0) + (1.0 if game["margin"] <= 3 else 0.0))
        facts.append({
            "category": "special_teams_game_swing",
            "importance": round(importance, 2),
            "evidence_type": "compound_derived_fact",
            "team": team,
            "opponent": game["opponent"],
            "matchup_margin": number(game["margin"]),
            "kicker": slots["K"].get("player"),
            "kicker_points": slots["K"].get("points"),
            "defense": slots["DEF"].get("player"),
            "defense_points": slots["DEF"].get("points"),
            "combined_k_def_points": number(combined),
            "headline_fact": f"{team} beat {game['opponent']} by {game['margin']:.2f} while getting {combined:.2f} combined points from {slots['K'].get('player')} at kicker and {slots['DEF'].get('player')} at defense.",
            "suppresses": ["kicker_impact", "defense_impact"],
        })

    # Acquisition payoff with result/margin context.
    for item in acquisitions:
        if not item.get("started"):
            continue
        team = item.get("team")
        game = matchup_by_team.get(team)
        if not game:
            continue
        pts = float(item.get("points", 0) or 0)
        materially_close = pts > game["margin"]
        if not game["won"] and not materially_close:
            continue
        importance = min(9.5, float(item.get("importance", 5)) + (1.0 if game["won"] else 0) + (0.75 if materially_close else 0))
        facts.append({
            **{k: v for k, v in item.items() if k not in {"category", "importance", "headline_fact"}},
            "category": "acquisition_payoff_win" if game["won"] else "acquisition_payoff_close_game",
            "importance": round(importance, 2),
            "evidence_type": "compound_derived_fact",
            "opponent": game["opponent"],
            "matchup_margin": number(game["margin"]),
            "team_won": game["won"],
            "headline_fact": f"{team} recently acquired {item.get('player')} and started him for {pts:.2f} points" + (f" in a {game['margin']:.2f}-point win over {game['opponent']}." if game["won"] else f" in a game decided by {game['margin']:.2f} points."),
            "suppresses": ["acquisition_hero"],
        })

    # Carry jobs become richer when the team lost / scored poorly / had lineup failures.
    for item in anomalies:
        if item.get("category") != "one_player_carry":
            continue
        team = item.get("team")
        game = matchup_by_team.get(team)
        if not game or not game["lost"]:
            continue
        share = float(item.get("share_of_team_score_pct", 0) or 0)
        if share < 35:
            continue
        related_manager = next((x for x in facts if x.get("team") == team and x.get("category") in {"manager_blew_game", "multiple_managerial_mistakes"}), None)
        facts.append({
            **{k: v for k, v in item.items() if k not in {"category", "importance", "headline_fact"}},
            "category": "carry_job_in_loss",
            "importance": round(min(9.5, float(item.get("importance", 6)) + 0.75 + (0.5 if related_manager else 0)), 2),
            "evidence_type": "compound_derived_fact",
            "opponent": game["opponent"],
            "loss_margin": number(game["margin"]),
            "headline_fact": f"{item.get('player')} supplied {share:.1f}% of {team}'s score, but {team} still lost to {game['opponent']} by {game['margin']:.2f}." + (" The same team also had multiple validated lineup mistakes." if related_manager else ""),
            "suppresses": ["one_player_carry"],
        })

    # Consequential starter dud: only if validated replacement gain could matter.
    for item in anomalies:
        if item.get("category") != "starter_dud":
            continue
        team = item.get("team")
        game = matchup_by_team.get(team)
        if not game or not game["lost"]:
            continue
        # A manager_blew_game story already owns this team's lineup-failure narrative.
        # Keep the dud as supporting evidence rather than a second headline.
        if any(x.get("category") == "manager_blew_game" and x.get("team") == team for x in facts):
            continue
        row = None
        if not bd.empty and "fantasy_team" in bd.columns:
            rows = bd[(bd["year"].eq(year)) & (bd["week"].eq(week)) & (bd["fantasy_team"].map(canon).eq(team))]
            if not rows.empty:
                row = rows.iloc[0]
        if row is None:
            continue
        gain = pd.to_numeric(row.get("optimization_gain"), errors="coerce")
        if pd.isna(gain):
            actual = pd.to_numeric(row.get("actual_score"), errors="coerce")
            optimal = pd.to_numeric(row.get("optimal_score"), errors="coerce")
            gain = optimal - actual if pd.notna(actual) and pd.notna(optimal) else np.nan
        if pd.isna(gain) or float(gain) <= game["margin"]:
            continue
        facts.append({
            "category": "starter_dud_cost_win",
            "importance": 8.75,
            "evidence_type": "compound_derived_fact",
            "team": team,
            "opponent": game["opponent"],
            "player": item.get("player"),
            "points": item.get("points"),
            "loss_margin": number(game["margin"]),
            "optimization_gain": number(gain),
            "headline_fact": f"{team} lost by {game['margin']:.2f} after starting {item.get('player')} for only {float(item.get('points', 0)):.2f} points; validated lineup optimization offered {float(gain):.2f} points, enough to change the result.",
            "suppresses": ["starter_dud"],
        })

    # Opponent contrast: a winner's special-teams edge paired with an opponent's
    # validated manager-caused loss is a richer matchup story than either fragment alone.
    blew_by_team = {x.get("team"): x for x in facts if x.get("category") == "manager_blew_game"}
    for st in special_teams:
        winner = st.get("team")
        game = matchup_by_team.get(winner)
        if not game or not game.get("won"):
            continue
        loser_story = blew_by_team.get(game.get("opponent"))
        if not loser_story:
            continue
        pts = float(st.get("points", 0) or 0)
        if pts < 15:
            continue
        facts.append({
            "category": "opponent_contrast",
            "importance": round(min(9.4, 8.2 + min(1.2, pts / 20.0)), 2),
            "evidence_type": "compound_derived_fact",
            "team": winner,
            "opponent": game["opponent"],
            "player": st.get("player"),
            "position": st.get("position"),
            "points": st.get("points"),
            "matchup_margin": number(game["margin"]),
            "opponent_optimization_gain": loser_story.get("optimization_gain"),
            "headline_fact": f"{winner} beat {game['opponent']} by {game['margin']:.2f} with {st.get('player')} scoring {pts:.2f} at {st.get('position')}, while {game['opponent']} had {float(loser_story.get('optimization_gain') or 0):.2f} points of validated lineup optimization available.",
            "suppresses": [],
        })

    # De-duplicate compound stories by category/team/player while keeping strongest.
    deduped = {}
    for fact in facts:
        key = (fact.get("category"), fact.get("team"), fact.get("player"))
        if key not in deduped or float(fact.get("importance", 0)) > float(deduped[key].get("importance", 0)):
            deduped[key] = fact
    return sorted(deduped.values(), key=lambda x: float(x.get("importance", 0)), reverse=True)


def build_story_candidates(
    special_teams,
    acquisitions,
    anomalies,
    historical_rarity,
    compound_stories=None,
):
    """Merge raw and compound facts into a diverse ranked editorial news desk."""
    compound_stories = compound_stories or []
    candidates = []

    # Compound stories lead the desk and can suppress weaker raw fragments
    # for the same team/category relationship.
    suppressed = set()
    for fact in compound_stories:
        item = dict(fact)
        item["source_section"] = "compound_stories"
        candidates.append(item)
        team = item.get("team")
        for category in item.get("suppresses", []):
            suppressed.add((team, category))

    for source_name, facts in [
        ("special_teams", special_teams),
        ("acquisitions", acquisitions),
        ("lineup_anomalies", anomalies),
        ("historical_rarity", historical_rarity),
    ]:
        for fact in facts:
            if (fact.get("team"), fact.get("category")) in suppressed:
                continue
            item = dict(fact)
            item["source_section"] = source_name
            candidates.append(item)

    candidates.sort(key=lambda x: (-float(x.get("importance", 0)), str(x.get("category", "")), str(x.get("team", ""))))

    # Diversity pass: no single raw category should monopolize the desk.
    selected = []
    category_counts = {}
    team_counts = {}
    matchup_counts = {}
    deferred = []

    def matchup_key(item):
        team, opp = item.get("team"), item.get("opponent")
        return tuple(sorted((str(team), str(opp)))) if team and opp else None

    for item in candidates:
        category = item.get("category", "")
        team = item.get("team", "")
        is_compound = item.get("source_section") == "compound_stories"
        category_cap = 4 if is_compound else 3
        team_cap = 3
        mkey = matchup_key(item)
        # In the headline portion of the desk, cap a matchup at two stories.
        # Defer additional good angles rather than deleting them entirely.
        if len(selected) < 6 and mkey and matchup_counts.get(mkey, 0) >= 2:
            deferred.append(item)
            continue
        if category_counts.get(category, 0) >= category_cap:
            continue
        if team and team_counts.get(team, 0) >= team_cap and not is_compound:
            continue
        selected.append(item)
        category_counts[category] = category_counts.get(category, 0) + 1
        if team:
            team_counts[team] = team_counts.get(team, 0) + 1
        if mkey:
            matchup_counts[mkey] = matchup_counts.get(mkey, 0) + 1
        # Once the six-story headline window is filled, immediately release
        # any high-value stories deferred only for matchup diversity. This
        # keeps one matchup from monopolizing the headlines without burying
        # a strong third angle at the bottom of the desk.
        if len(selected) >= 6 and deferred:
            for deferred_item in deferred:
                if len(selected) >= 30:
                    break
                d_category = deferred_item.get("category", "")
                d_team = deferred_item.get("team", "")
                d_is_compound = deferred_item.get("source_section") == "compound_stories"
                if category_counts.get(d_category, 0) >= (4 if d_is_compound else 3):
                    continue
                if d_team and team_counts.get(d_team, 0) >= 4:
                    continue
                selected.append(deferred_item)
                category_counts[d_category] = category_counts.get(d_category, 0) + 1
                if d_team:
                    team_counts[d_team] = team_counts.get(d_team, 0) + 1
            deferred = []

        if len(selected) >= 30:
            break

    for item in deferred:
        if len(selected) >= 30:
            break
        category = item.get("category", "")
        team = item.get("team", "")
        is_compound = item.get("source_section") == "compound_stories"
        if category_counts.get(category, 0) >= (4 if is_compound else 3):
            continue
        if team and team_counts.get(team, 0) >= 4:
            continue
        selected.append(item)
        category_counts[category] = category_counts.get(category, 0) + 1
        if team:
            team_counts[team] = team_counts.get(team, 0) + 1

    return selected

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

    # Weekly Story Engine: deterministic, evidence-backed color for the writers.
    special_teams = special_teams_facts(
        lineups, matchups, CURRENT_SEASON, week
    )
    acquisitions = acquisition_impact_facts(
        transactions, lineups, CURRENT_SEASON, week
    )
    anomalies = lineup_anomaly_facts(
        lineups, efficiency, CURRENT_SEASON, week
    )
    historical_rarity = historical_rarity_facts(
        matchups, CURRENT_SEASON, week
    )
    compound_stories = compound_story_facts(
        lineups, efficiency, matchups, special_teams, acquisitions, anomalies,
        CURRENT_SEASON, week
    )
    story_candidates = build_story_candidates(
        special_teams, acquisitions, anomalies, historical_rarity, compound_stories
    )

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
        "weekly_story_engine": {
            "special_teams": special_teams,
            "acquisition_impact": acquisitions,
            "lineup_anomalies": anomalies,
            "historical_rarity": historical_rarity,
            "compound_stories": compound_stories,
            "story_candidates": story_candidates,
        },
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
        "PASS — story candidates: "
        f"{len(packet['weekly_story_engine']['story_candidates'])} "
        "ranked nuggets"
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