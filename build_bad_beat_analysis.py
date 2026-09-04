from pathlib import Path

import numpy as np
import pandas as pd

from season_config import (
    LAST_COMPLETED_SEASON,
    detect_latest_completed_week,
    filter_weekly_current_matchups,
    print_season_config,
)
from team_aliases import canonical_team


# ============================================================
# PATHS
# ============================================================

MATCHUP_CANDIDATES = [
    Path(
        f"data/all_matchups_clean_2017_"
        f"{LAST_COMPLETED_SEASON}.csv"
    ),
    Path("data/all_matchups_clean.csv"),
]

OUTPUT_DIR = Path("data/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FIND MATCHUP MASTER
# ============================================================

def find_matchup_file():
    stable = Path("data/all_matchups_clean.csv")
    if not stable.exists():
        raise FileNotFoundError(stable)
    return stable


def build_team_weeks(matchups):

    rows = []

    for _, game in matchups.iterrows():

        rows.append(
            {
                "year": int(game["year"]),
                "week": int(game["week"]),
                "fantasy_team": game["team_1"],
                "opponent": game["team_2"],
                "score": float(game["team_1_score"]),
                "opponent_score": float(game["team_2_score"]),
            }
        )

        rows.append(
            {
                "year": int(game["year"]),
                "week": int(game["week"]),
                "fantasy_team": game["team_2"],
                "opponent": game["team_1"],
                "score": float(game["team_2_score"]),
                "opponent_score": float(game["team_1_score"]),
            }
        )

    df = pd.DataFrame(rows)

    df["canonical_team"] = (
        df["fantasy_team"]
        .apply(canonical_team)
    )

    df["canonical_opponent"] = (
        df["opponent"]
        .apply(canonical_team)
    )

    df["margin"] = (
        df["score"]
        - df["opponent_score"]
    )

    df["win"] = (
        df["score"]
        > df["opponent_score"]
    ).astype(int)

    df["loss"] = (
        df["score"]
        < df["opponent_score"]
    ).astype(int)

    df["tie"] = (
        df["score"]
        == df["opponent_score"]
    ).astype(int)

    return df


# ============================================================
# ALL-PLAY / WEEKLY STRENGTH
# ============================================================

def add_all_play(team_weeks):

    frames = []

    for (year, week), group in team_weeks.groupby(
        ["year", "week"],
        sort=True,
    ):

        group = group.copy()

        scores = group["score"].to_numpy(dtype=float)

        all_play_wins = []
        all_play_losses = []
        all_play_ties = []
        expected_win_rates = []
        weekly_ranks = []

        for score in scores:

            other_scores = scores[scores != score]

            # If duplicate scores exist, removing by value would remove
            # both rows. Recalculate explicitly below using indexes.
            all_play_wins.append(np.nan)
            all_play_losses.append(np.nan)
            all_play_ties.append(np.nan)
            expected_win_rates.append(np.nan)
            weekly_ranks.append(np.nan)

        for idx in group.index:

            score = float(group.loc[idx, "score"])

            others = group.loc[
                group.index != idx,
                "score",
            ].astype(float)

            wins = int((score > others).sum())
            losses = int((score < others).sum())
            ties = int((score == others).sum())

            possible = len(others)

            expected = (
                (wins + 0.5 * ties) / possible
                if possible
                else np.nan
            )

            rank = (
                1
                + int((others > score).sum())
            )

            group.loc[idx, "all_play_wins"] = wins
            group.loc[idx, "all_play_losses"] = losses
            group.loc[idx, "all_play_ties"] = ties
            group.loc[idx, "expected_win_rate"] = expected
            group.loc[idx, "weekly_score_rank"] = rank
            group.loc[idx, "teams_that_week"] = len(group)

        frames.append(group)

    return pd.concat(
        frames,
        ignore_index=True,
    )


# ============================================================
# BAD BEAT METRICS
# ============================================================

def add_bad_beat_metrics(df):

    df = df.copy()

    # Expected result minus actual result.
    #
    # Example:
    # Expected win rate = .91
    # Actual result = loss (0)
    # Luck swing = +.91 against the team.
    #
    # Positive = unlucky
    # Negative = fortunate.

    df["bad_beat_value"] = (
        df["expected_win_rate"]
        - df["win"]
        - (0.5 * df["tie"])
    )

    # Loss despite being better than at least half the league.
    df["bad_beat"] = (
        (df["loss"] == 1)
        & (df["expected_win_rate"] >= 0.50)
    ).astype(int)

    # Severe bad beat:
    # lost despite a score that would beat at least 75% of
    # the other teams that week.
    df["severe_bad_beat"] = (
        (df["loss"] == 1)
        & (df["expected_win_rate"] >= 0.75)
    ).astype(int)

    # Brutal bad beat:
    # lost despite being one of the week's top 3 scores.
    df["brutal_bad_beat"] = (
        (df["loss"] == 1)
        & (df["weekly_score_rank"] <= 3)
    ).astype(int)

    # Lucky win:
    # won despite a score that would lose to at least half
    # of the league.
    df["lucky_win"] = (
        (df["win"] == 1)
        & (df["expected_win_rate"] <= 0.50)
    ).astype(int)

    # Severe lucky win.
    df["severe_lucky_win"] = (
        (df["win"] == 1)
        & (df["expected_win_rate"] <= 0.25)
    ).astype(int)

    return df


# ============================================================
# SUMMARY BUILDERS
# ============================================================

def summarize_franchise(df):

    summary = (
        df.groupby(
            "canonical_team",
            as_index=False,
        )
        .agg(
            team_weeks=("score", "size"),
            actual_wins=("win", "sum"),
            expected_wins=("expected_win_rate", "sum"),
            bad_beats=("bad_beat", "sum"),
            severe_bad_beats=("severe_bad_beat", "sum"),
            brutal_bad_beats=("brutal_bad_beat", "sum"),
            lucky_wins=("lucky_win", "sum"),
            severe_lucky_wins=("severe_lucky_win", "sum"),
            avg_score=("score", "mean"),
            avg_expected_win_rate=(
                "expected_win_rate",
                "mean",
            ),
            total_bad_beat_value=(
                "bad_beat_value",
                "sum",
            ),
        )
    )

    summary["actual_win_rate"] = (
        summary["actual_wins"]
        / summary["team_weeks"]
    )

    summary["expected_win_rate"] = (
        summary["expected_wins"]
        / summary["team_weeks"]
    )

    # Positive = fewer actual wins than all-play expectation.
    summary["wins_below_expected"] = (
        summary["expected_wins"]
        - summary["actual_wins"]
    )

    summary["bad_beat_rate"] = (
        summary["bad_beats"]
        / summary["team_weeks"]
    )

    summary["lucky_win_rate"] = (
        summary["lucky_wins"]
        / summary["team_weeks"]
    )

    return summary.sort_values(
        [
            "wins_below_expected",
            "severe_bad_beats",
        ],
        ascending=[
            False,
            False,
        ],
    )


def summarize_season(df):

    summary = (
        df.groupby(
            [
                "year",
                "canonical_team",
            ],
            as_index=False,
        )
        .agg(
            team_weeks=("score", "size"),
            actual_wins=("win", "sum"),
            expected_wins=("expected_win_rate", "sum"),
            bad_beats=("bad_beat", "sum"),
            severe_bad_beats=("severe_bad_beat", "sum"),
            brutal_bad_beats=("brutal_bad_beat", "sum"),
            lucky_wins=("lucky_win", "sum"),
            severe_lucky_wins=("severe_lucky_win", "sum"),
            avg_score=("score", "mean"),
        )
    )

    summary["actual_win_rate"] = (
        summary["actual_wins"]
        / summary["team_weeks"]
    )

    summary["expected_win_rate"] = (
        summary["expected_wins"]
        / summary["team_weeks"]
    )

    summary["wins_below_expected"] = (
        summary["expected_wins"]
        - summary["actual_wins"]
    )

    return summary.sort_values(
        [
            "year",
            "wins_below_expected",
        ],
        ascending=[
            True,
            False,
        ],
    )


# ============================================================
# MAIN
# ============================================================

def main():

    matchup_file = find_matchup_file()

    print("=" * 72)
    print("BUILDING BAD BEAT ANALYSIS")
    print("=" * 72)
    print_season_config()

    print(f"\nMatchup source: {matchup_file}")

    matchups = pd.read_csv(matchup_file)

    matchups["year"] = pd.to_numeric(
        matchups["year"],
        errors="coerce",
    )

    if matchups["year"].isna().any():
        raise RuntimeError(
            "Matchup input contains "
            f"{int(matchups['year'].isna().sum())} invalid year rows."
        )

    matchups["year"] = matchups["year"].astype(int)

    weekly_state = detect_latest_completed_week(matchups)
    matchups = filter_weekly_current_matchups(
        matchups, weekly_state=weekly_state
    )
    print_season_config(weekly_state)

    if matchups.empty:
        raise RuntimeError(
            "No completed-season regular-season matchups remain."
        )

    print(
        f"Regular-season games: {len(matchups):,}"
    )

    years = sorted(
        matchups["year"]
        .dropna()
        .astype(int)
        .unique()
    )

    print(
        "Years:",
        ", ".join(map(str, years)),
    )

    team_weeks = build_team_weeks(matchups)

    print(
        f"Team-weeks: {len(team_weeks):,}"
    )

    team_weeks = add_all_play(team_weeks)
    team_weeks = add_bad_beat_metrics(team_weeks)

    franchise = summarize_franchise(team_weeks)
    season = summarize_season(team_weeks)

    # Individual historical bad beats.
    bad_beats = (
        team_weeks[
            team_weeks["loss"] == 1
        ]
        .copy()
        .sort_values(
            [
                "bad_beat_value",
                "score",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

    # Individual historical lucky wins.
    lucky_wins = (
        team_weeks[
            team_weeks["win"] == 1
        ]
        .copy()
        .sort_values(
            [
                "bad_beat_value",
                "score",
            ],
            ascending=[
                True,
                True,
            ],
        )
    )

    # Weekly league-level summary.
    weekly = (
        team_weeks.groupby(
            [
                "year",
                "week",
            ],
            as_index=False,
        )
        .agg(
            avg_score=("score", "mean"),
            high_score=("score", "max"),
            low_score=("score", "min"),
            bad_beats=("bad_beat", "sum"),
            severe_bad_beats=("severe_bad_beat", "sum"),
            brutal_bad_beats=("brutal_bad_beat", "sum"),
            lucky_wins=("lucky_win", "sum"),
        )
    )

    if (
        pd.to_numeric(
            team_weeks["year"],
            errors="coerce",
        ) > weekly_state.current_season
    ).any():
        raise RuntimeError(
            "Incomplete/future season leaked into Bad Beat output."
        )

    season_team_counts = (
        team_weeks.groupby("year")["fantasy_team"]
        .nunique()
        .sort_index()
    )

    bad_season_counts = season_team_counts[
        season_team_counts != 12
    ]

    if not bad_season_counts.empty:
        raise RuntimeError(
            "Expected 12 teams in every completed season; found: "
            + str(bad_season_counts.to_dict())
        )

    if weekly_state.latest_completed_week == 0:
        baseline_checks = {
            "regular-season games": (
                len(matchups),
                732,
            ),
            "team-weeks": (
                len(team_weeks),
                1464,
            ),
            "bad beats": (
                int(team_weeks["bad_beat"].sum()),
                166,
            ),
            "severe bad beats": (
                int(team_weeks["severe_bad_beat"].sum()),
                29,
            ),
            "brutal top-3-score losses": (
                int(team_weeks["brutal_bad_beat"].sum()),
                29,
            ),
            "lucky wins": (
                int(team_weeks["lucky_win"].sum()),
                166,
            ),
        }

        for label, (actual, expected) in baseline_checks.items():
            if actual != expected:
                raise RuntimeError(
                    f"Audited 2017-2025 {label} regression failed: "
                    f"expected {expected:,}, found {actual:,}."
                )

        print(
            "PASS — audited 2017-2025 Bad Beat baseline "
            "(732 games / 1,464 team-weeks / "
            "166 bad beats / 29 severe / "
            "29 brutal / 166 lucky wins)."
        )

    outputs = {
        "bad_beat_team_week.csv": team_weeks,
        "bad_beat_franchise.csv": franchise,
        "bad_beat_season.csv": season,
        "bad_beat_history.csv": bad_beats,
        "lucky_win_history.csv": lucky_wins,
        "bad_beat_weekly.csv": weekly,
    }

    for filename, frame in outputs.items():

        path = OUTPUT_DIR / filename
        frame.to_csv(
            path,
            index=False,
        )

        print(
            f"Wrote {path} "
            f"({len(frame):,} rows)"
        )

    print("\n" + "=" * 72)
    print("VALIDATION")
    print("=" * 72)

    expected_team_weeks = len(matchups) * 2

    assert len(team_weeks) == expected_team_weeks

    assert team_weeks[
        [
            "year",
            "week",
            "fantasy_team",
        ]
    ].duplicated().sum() == 0

    assert team_weeks[
        "expected_win_rate"
    ].between(0, 1).all()

    assert (
        team_weeks["all_play_wins"]
        + team_weeks["all_play_losses"]
        + team_weeks["all_play_ties"]
        == team_weeks["teams_that_week"] - 1
    ).all()

    print(
        f"PASS — {len(team_weeks):,} unique team-weeks."
    )

    print(
        "PASS — expected win rates are between 0 and 1."
    )

    print(
        "PASS — all-play records reconcile."
    )

    print(
        "PASS — every completed season contains 12 teams."
    )

    print("\n" + "=" * 72)
    print("LEAGUE BAD BEAT SUMMARY")
    print("=" * 72)

    print(
        f"Bad beats: "
        f"{int(team_weeks['bad_beat'].sum())}"
    )

    print(
        f"Severe bad beats: "
        f"{int(team_weeks['severe_bad_beat'].sum())}"
    )

    print(
        f"Brutal top-3-score losses: "
        f"{int(team_weeks['brutal_bad_beat'].sum())}"
    )

    print(
        f"Lucky wins: "
        f"{int(team_weeks['lucky_win'].sum())}"
    )

    print("\nMost unlucky franchises:")
    print(
        franchise[
            [
                "canonical_team",
                "team_weeks",
                "actual_wins",
                "expected_wins",
                "wins_below_expected",
                "bad_beats",
                "severe_bad_beats",
                "lucky_wins",
            ]
        ]
        .head(15)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    print("\nWorst individual bad beats:")
    print(
        bad_beats[
            [
                "year",
                "week",
                "canonical_team",
                "canonical_opponent",
                "score",
                "opponent_score",
                "weekly_score_rank",
                "expected_win_rate",
                "bad_beat_value",
            ]
        ]
        .head(15)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )


if __name__ == "__main__":
    main()
