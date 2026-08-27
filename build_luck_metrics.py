from pathlib import Path
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"
MATCHUPS_FILE = DATA_DIR / "all_matchups_2018_2025.csv"

OUT_DIR = DATA_DIR / "analysis"
TEAM_WEEK_OUT = OUT_DIR / "luck_team_week.csv"
SEASON_OUT = OUT_DIR / "luck_season.csv"
ALL_TIME_OUT = OUT_DIR / "luck_all_time.csv"


def banner(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


def find_col(df, candidates, label):
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(
        f"Could not find {label}. Tried: {candidates}\n"
        f"Available columns: {list(df.columns)}"
    )


def pct_rank_high_is_hard(series):
    # 100 = hardest / highest opponent scoring.
    return series.rank(method="average", pct=True) * 100


def luck_label(x):
    if x >= 2.5:
        return "Extremely Lucky"
    if x >= 1.0:
        return "Lucky"
    if x <= -2.5:
        return "Cursed"
    if x <= -1.0:
        return "Unlucky"
    return "Neutral"


def main():
    banner("BUILDING FANTASY FOOTBALL LUCK + STRENGTH OF SCHEDULE METRICS")

    if not MATCHUPS_FILE.exists():
        raise FileNotFoundError(f"Missing master matchup file: {MATCHUPS_FILE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(MATCHUPS_FILE)

    year_col = find_col(raw, ["year", "season"], "year")
    week_col = find_col(raw, ["week"], "week")
    t1_col = find_col(raw, ["team_1", "left_team", "team1"], "team 1")
    t2_col = find_col(raw, ["team_2", "right_team", "team2"], "team 2")
    s1_col = find_col(raw, ["team_1_score", "left_score", "team1_score"], "team 1 score")
    s2_col = find_col(raw, ["team_2_score", "right_score", "team2_score"], "team 2 score")

    raw[year_col] = pd.to_numeric(raw[year_col], errors="raise").astype(int)
    raw[week_col] = pd.to_numeric(raw[week_col], errors="raise").astype(int)
    raw[s1_col] = pd.to_numeric(raw[s1_col], errors="coerce")
    raw[s2_col] = pd.to_numeric(raw[s2_col], errors="coerce")

    banner("1. MASTER MATCHUP INPUT")
    print(f"Rows: {len(raw):,}")
    print(f"Seasons: {raw[year_col].min()}-{raw[year_col].max()}")

    # Convert every matchup into two team-week rows.
    left = pd.DataFrame({
        "year": raw[year_col],
        "week": raw[week_col],
        "fantasy_team": raw[t1_col],
        "opponent": raw[t2_col],
        "team_score": raw[s1_col],
        "opponent_score": raw[s2_col],
    })

    right = pd.DataFrame({
        "year": raw[year_col],
        "week": raw[week_col],
        "fantasy_team": raw[t2_col],
        "opponent": raw[t1_col],
        "team_score": raw[s2_col],
        "opponent_score": raw[s1_col],
    })

    tw = pd.concat([left, right], ignore_index=True)

    tw["actual_win"] = (tw["team_score"] > tw["opponent_score"]).astype(float)
    tw["actual_loss"] = (tw["team_score"] < tw["opponent_score"]).astype(float)
    tw["actual_tie"] = (tw["team_score"] == tw["opponent_score"]).astype(float)
    tw["actual_win_value"] = tw["actual_win"] + 0.5 * tw["actual_tie"]
    tw["margin"] = tw["team_score"] - tw["opponent_score"]

    banner("2. CALCULATING WEEKLY ALL-PLAY EXPECTED WINS")

    weekly_rows = []

    for (year, week), group in tw.groupby(["year", "week"], sort=True):
        if len(group) != 12 or group["fantasy_team"].nunique() != 12:
            raise RuntimeError(
                f"{year} Week {week}: expected 12 team rows, found "
                f"{len(group)} rows / {group['fantasy_team'].nunique()} teams."
            )

        scores = group.set_index("fantasy_team")["team_score"].to_dict()

        score_values = list(scores.values())
        sorted_scores = sorted(score_values, reverse=True)

        for _, row in group.iterrows():
            team = row["fantasy_team"]
            score = float(row["team_score"])

            other_scores = [
                float(v) for t, v in scores.items()
                if t != team
            ]

            wins_vs_field = sum(score > x for x in other_scores)
            ties_vs_field = sum(score == x for x in other_scores)
            losses_vs_field = sum(score < x for x in other_scores)

            expected_win_value = (
                wins_vs_field + 0.5 * ties_vs_field
            ) / 11.0

            rank = 1 + sum(x > score for x in score_values)

            top3 = rank <= 3
            bottom3 = rank >= 10

            opp_score = float(row["opponent_score"])
            opp_rank = 1 + sum(x > opp_score for x in score_values)

            weekly_rows.append({
                **row.to_dict(),
                "all_play_wins": wins_vs_field,
                "all_play_losses": losses_vs_field,
                "all_play_ties": ties_vs_field,
                "expected_win_value": expected_win_value,
                "weekly_schedule_luck": (
                    float(row["actual_win_value"]) - expected_win_value
                ),
                "weekly_score_rank": rank,
                "top_3_score": bool(top3),
                "bottom_3_score": bool(bottom3),
                "opponent_weekly_score_rank": opp_rank,
                "opponent_top_3_score": bool(opp_rank <= 3),
                "opponent_bottom_3_score": bool(opp_rank >= 10),
                "close_game_5": bool(abs(float(row["margin"])) <= 5),
                "close_game_10": bool(abs(float(row["margin"])) <= 10),
                "close_game_5_win_value": (
                    float(row["actual_win_value"])
                    if abs(float(row["margin"])) <= 5
                    else np.nan
                ),
                "close_game_10_win_value": (
                    float(row["actual_win_value"])
                    if abs(float(row["margin"])) <= 10
                    else np.nan
                ),
            })

    team_week = pd.DataFrame(weekly_rows)

    if len(team_week) != len(tw):
        raise RuntimeError("Team-week row count changed during calculation.")

    print(f"[PASS] Team-weeks calculated: {len(team_week):,}")

    banner("3. SEASON LUCK METRICS")

    season = (
        team_week
        .groupby(["year", "fantasy_team"], as_index=False)
        .agg(
            games=("actual_win_value", "size"),
            wins=("actual_win", "sum"),
            losses=("actual_loss", "sum"),
            ties=("actual_tie", "sum"),
            actual_win_value=("actual_win_value", "sum"),
            expected_wins=("expected_win_value", "sum"),
            points_for=("team_score", "sum"),
            points_against=("opponent_score", "sum"),
            avg_points_for=("team_score", "mean"),
            strength_of_schedule=("opponent_score", "mean"),
            all_play_wins=("all_play_wins", "sum"),
            all_play_losses=("all_play_losses", "sum"),
            all_play_ties=("all_play_ties", "sum"),
            opponent_top_3_weeks=("opponent_top_3_score", "sum"),
            opponent_bottom_3_weeks=("opponent_bottom_3_score", "sum"),
            own_top_3_weeks=("top_3_score", "sum"),
            own_bottom_3_weeks=("bottom_3_score", "sum"),
            close_games_5=("close_game_5", "sum"),
            close_games_10=("close_game_10", "sum"),
            close_game_5_win_value=("close_game_5_win_value", "sum"),
            close_game_10_win_value=("close_game_10_win_value", "sum"),
        )
    )

    season["schedule_luck_wins"] = (
        season["actual_win_value"] - season["expected_wins"]
    )

    season["actual_win_pct"] = (
        season["actual_win_value"] / season["games"] * 100
    )

    season["expected_win_pct"] = (
        season["expected_wins"] / season["games"] * 100
    )

    all_play_games = (
        season["all_play_wins"]
        + season["all_play_losses"]
        + season["all_play_ties"]
    )

    season["all_play_win_pct"] = np.where(
        all_play_games > 0,
        (
            season["all_play_wins"]
            + 0.5 * season["all_play_ties"]
        ) / all_play_games * 100,
        np.nan,
    )

    season["close_game_5_win_pct"] = np.where(
        season["close_games_5"] > 0,
        season["close_game_5_win_value"]
        / season["close_games_5"] * 100,
        np.nan,
    )

    season["close_game_10_win_pct"] = np.where(
        season["close_games_10"] > 0,
        season["close_game_10_win_value"]
        / season["close_games_10"] * 100,
        np.nan,
    )

    season["sos_percentile"] = (
        season.groupby("year")["strength_of_schedule"]
        .transform(pct_rank_high_is_hard)
    )

    season["sos_rank_hardest"] = (
        season.groupby("year")["strength_of_schedule"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    season["luck_rank"] = (
        season.groupby("year")["schedule_luck_wins"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    season["luck_label"] = season["schedule_luck_wins"].apply(luck_label)

    banner("4. ALL-TIME TEAM-NAME SUMMARY")

    all_time = (
        season
        .groupby("fantasy_team", as_index=False)
        .agg(
            seasons=("year", "nunique"),
            games=("games", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            ties=("ties", "sum"),
            actual_win_value=("actual_win_value", "sum"),
            expected_wins=("expected_wins", "sum"),
            points_for=("points_for", "sum"),
            points_against=("points_against", "sum"),
            all_play_wins=("all_play_wins", "sum"),
            all_play_losses=("all_play_losses", "sum"),
            all_play_ties=("all_play_ties", "sum"),
            opponent_top_3_weeks=("opponent_top_3_weeks", "sum"),
            opponent_bottom_3_weeks=("opponent_bottom_3_weeks", "sum"),
            close_games_5=("close_games_5", "sum"),
            close_game_5_win_value=("close_game_5_win_value", "sum"),
            close_games_10=("close_games_10", "sum"),
            close_game_10_win_value=("close_game_10_win_value", "sum"),
        )
    )

    all_time["schedule_luck_wins"] = (
        all_time["actual_win_value"] - all_time["expected_wins"]
    )

    all_time["actual_win_pct"] = (
        all_time["actual_win_value"] / all_time["games"] * 100
    )

    all_time["expected_win_pct"] = (
        all_time["expected_wins"] / all_time["games"] * 100
    )

    all_play_games = (
        all_time["all_play_wins"]
        + all_time["all_play_losses"]
        + all_time["all_play_ties"]
    )

    all_time["all_play_win_pct"] = (
        (
            all_time["all_play_wins"]
            + 0.5 * all_time["all_play_ties"]
        )
        / all_play_games
        * 100
    )

    all_time["avg_opponent_score"] = (
        all_time["points_against"] / all_time["games"]
    )

    all_time["close_game_5_win_pct"] = np.where(
        all_time["close_games_5"] > 0,
        all_time["close_game_5_win_value"]
        / all_time["close_games_5"] * 100,
        np.nan,
    )

    all_time["close_game_10_win_pct"] = np.where(
        all_time["close_games_10"] > 0,
        all_time["close_game_10_win_value"]
        / all_time["close_games_10"] * 100,
        np.nan,
    )

    all_time["luck_rank"] = (
        all_time["schedule_luck_wins"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    all_time["luck_label"] = all_time["schedule_luck_wins"].apply(luck_label)

    banner("5. VALIDATION")

    expected_team_weeks = len(raw) * 2

    if len(team_week) != expected_team_weeks:
        raise RuntimeError(
            f"Expected {expected_team_weeks} team-weeks, "
            f"found {len(team_week)}."
        )

    # Across the entire league, schedule luck must net to ~0 because
    # actual league wins and all-play-derived expected wins balance.
    net_luck = team_week["weekly_schedule_luck"].sum()

    if abs(net_luck) > 1e-8:
        raise RuntimeError(
            f"League-wide schedule luck should net to zero; got {net_luck}."
        )

    if not team_week["expected_win_value"].between(0, 1).all():
        raise RuntimeError("Expected win values outside 0-1.")

    print(f"[PASS] Team-weeks: {len(team_week):,}")
    print(f"[PASS] League-wide schedule luck nets to {net_luck:.8f}")
    print("[PASS] Expected win values are all between 0 and 1.")

    banner("6. SAVING FILES")

    team_week.to_csv(TEAM_WEEK_OUT, index=False)
    season.to_csv(SEASON_OUT, index=False)
    all_time.to_csv(ALL_TIME_OUT, index=False)

    print(TEAM_WEEK_OUT)
    print(SEASON_OUT)
    print(ALL_TIME_OUT)

    banner("LUCK METRICS BUILD COMPLETE")

    print()
    print("Luckiest single seasons:")
    print(
        season.sort_values(
            "schedule_luck_wins",
            ascending=False,
        )[
            [
                "year",
                "fantasy_team",
                "wins",
                "expected_wins",
                "schedule_luck_wins",
                "strength_of_schedule",
                "all_play_win_pct",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("Unluckiest single seasons:")
    print(
        season.sort_values(
            "schedule_luck_wins",
            ascending=True,
        )[
            [
                "year",
                "fantasy_team",
                "wins",
                "expected_wins",
                "schedule_luck_wins",
                "strength_of_schedule",
                "all_play_win_pct",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print(
        "NOTE: This first build measures schedule/matchup luck. "
        "It intentionally does NOT call poor player performances 'injury luck' "
        "without reliable historical injury-status data."
    )


if __name__ == "__main__":
    main()