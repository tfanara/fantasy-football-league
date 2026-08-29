from pathlib import Path

import numpy as np
import pandas as pd

from team_aliases import canonical_team


# ============================================================
# PATHS
# ============================================================

EFFICIENCY_DIR = Path(
    "data/matchups/player_week_stats/analysis"
)

TEAM_WEEK_FILE = (
    EFFICIENCY_DIR
    / "lineup_efficiency_team_week.csv"
)

DECISIONS_FILE = (
    EFFICIENCY_DIR
    / "lineup_efficiency_decisions.csv"
)

OUTPUT_DIR = Path("data/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD
# ============================================================

def load_data():

    if not TEAM_WEEK_FILE.exists():
        raise FileNotFoundError(
            f"Missing {TEAM_WEEK_FILE}"
        )

    if not DECISIONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {DECISIONS_FILE}"
        )

    team_week = pd.read_csv(
        TEAM_WEEK_FILE
    )

    decisions = pd.read_csv(
        DECISIONS_FILE
    )

    return team_week, decisions


# ============================================================
# ADD OPPONENT SCORE
# ============================================================

def add_opponent_score(df):

    df = df.copy()

    opponent_lookup = (
        df[
            [
                "year",
                "week",
                "fantasy_team",
                "actual_score",
            ]
        ]
        .rename(
            columns={
                "fantasy_team":
                    "opponent_lookup",
                "actual_score":
                    "opponent_score",
            }
        )
    )

    df = df.merge(
        opponent_lookup,
        left_on=[
            "year",
            "week",
            "opponent",
        ],
        right_on=[
            "year",
            "week",
            "opponent_lookup",
        ],
        how="left",
        validate="many_to_one",
    )

    df = df.drop(
        columns=["opponent_lookup"]
    )

    return df


# ============================================================
# OUTCOME METRICS
# ============================================================

def add_outcome_metrics(df):

    df = df.copy()

    df["canonical_team"] = (
        df["fantasy_team"]
        .apply(canonical_team)
    )

    df["canonical_opponent"] = (
        df["opponent"]
        .apply(canonical_team)
    )

    df["actual_win"] = (
        df["actual_score"]
        > df["opponent_score"]
    ).astype(int)

    df["actual_loss"] = (
        df["actual_score"]
        < df["opponent_score"]
    ).astype(int)

    df["actual_tie"] = (
        df["actual_score"]
        == df["opponent_score"]
    ).astype(int)

    df["optimal_win"] = (
        df["optimal_score"]
        > df["opponent_score"]
    ).astype(int)

    df["optimal_loss"] = (
        df["optimal_score"]
        < df["opponent_score"]
    ).astype(int)

    df["optimal_tie"] = (
        df["optimal_score"]
        == df["opponent_score"]
    ).astype(int)

    # --------------------------------------------------------
    # MANAGER-CAUSED LOSS
    #
    # Actual lineup lost, but optimal lineup would have won.
    # --------------------------------------------------------

    df["manager_caused_loss"] = (
        (df["actual_loss"] == 1)
        & (df["optimal_win"] == 1)
    ).astype(int)

    # Actual loss where optimal lineup would at least tie.
    df["manager_caused_nonwin"] = (
        (df["actual_loss"] == 1)
        & (
            (df["optimal_win"] == 1)
            | (df["optimal_tie"] == 1)
        )
    ).astype(int)

    df["actual_margin"] = (
        df["actual_score"]
        - df["opponent_score"]
    )

    df["optimal_margin"] = (
        df["optimal_score"]
        - df["opponent_score"]
    )

    df["loss_margin"] = np.where(
        df["actual_loss"] == 1,
        df["opponent_score"]
        - df["actual_score"],
        np.nan,
    )

    # How much better the optimal lineup was.
    df["optimization_gain"] = (
        df["optimal_score"]
        - df["actual_score"]
    )

    # For manager-caused losses, how comfortably the
    # optimal lineup would have won.
    df["would_have_won_by"] = np.where(
        df["manager_caused_loss"] == 1,
        df["optimal_score"]
        - df["opponent_score"],
        np.nan,
    )

    # A painful close-loss indicator:
    # points left on bench exceeded actual loss margin.
    df["bench_points_exceeded_loss_margin"] = (
        (df["actual_loss"] == 1)
        & (
            df["points_left_on_bench"]
            > df["loss_margin"]
        )
    ).astype(int)

    return df


# ============================================================
# FRANCHISE SUMMARY
# ============================================================

def build_franchise_summary(df):

    summary = (
        df.groupby(
            "canonical_team",
            as_index=False,
        )
        .agg(
            team_weeks=(
                "actual_score",
                "size",
            ),
            actual_wins=(
                "actual_win",
                "sum",
            ),
            actual_losses=(
                "actual_loss",
                "sum",
            ),
            manager_caused_losses=(
                "manager_caused_loss",
                "sum",
            ),
            total_points_left=(
                "points_left_on_bench",
                "sum",
            ),
            avg_points_left_per_week=(
                "points_left_on_bench",
                "mean",
            ),
            avg_lineup_efficiency_pct=(
                "lineup_efficiency_pct",
                "mean",
            ),
            avoidable_starts=(
                "avoidable_start_count",
                "sum",
            ),
            missed_starts=(
                "missed_start_count",
                "sum",
            ),
            worst_week_points_left=(
                "points_left_on_bench",
                "max",
            ),
            avg_optimization_gain=(
                "optimization_gain",
                "mean",
            ),
        )
    )

    summary["manager_caused_loss_rate"] = np.where(
        summary["actual_losses"] > 0,
        (
            summary["manager_caused_losses"]
            / summary["actual_losses"]
        ),
        np.nan,
    )

    summary["manager_caused_loss_week_rate"] = (
        summary["manager_caused_losses"]
        / summary["team_weeks"]
    )

    summary["wins_with_optimal_lineup"] = (
        summary["actual_wins"]
        + summary["manager_caused_losses"]
    )

    return summary.sort_values(
        [
            "manager_caused_losses",
            "avg_points_left_per_week",
        ],
        ascending=[
            False,
            False,
        ],
    )


# ============================================================
# SEASON SUMMARY
# ============================================================

def build_season_summary(df):

    summary = (
        df.groupby(
            [
                "year",
                "canonical_team",
            ],
            as_index=False,
        )
        .agg(
            weeks=(
                "actual_score",
                "size",
            ),
            actual_wins=(
                "actual_win",
                "sum",
            ),
            actual_losses=(
                "actual_loss",
                "sum",
            ),
            manager_caused_losses=(
                "manager_caused_loss",
                "sum",
            ),
            total_points_left=(
                "points_left_on_bench",
                "sum",
            ),
            avg_points_left_per_week=(
                "points_left_on_bench",
                "mean",
            ),
            avg_lineup_efficiency_pct=(
                "lineup_efficiency_pct",
                "mean",
            ),
            avoidable_starts=(
                "avoidable_start_count",
                "sum",
            ),
            worst_week_points_left=(
                "points_left_on_bench",
                "max",
            ),
        )
    )

    summary["manager_caused_loss_rate"] = np.where(
        summary["actual_losses"] > 0,
        (
            summary["manager_caused_losses"]
            / summary["actual_losses"]
        ),
        np.nan,
    )

    summary["wins_with_optimal_lineup"] = (
        summary["actual_wins"]
        + summary["manager_caused_losses"]
    )

    return summary.sort_values(
        [
            "year",
            "manager_caused_losses",
        ],
        ascending=[
            True,
            False,
        ],
    )


# ============================================================
# PLAYER / DECISION SUMMARY
# ============================================================

def build_player_decision_summary(decisions):

    decisions = decisions.copy()

    decisions["canonical_team"] = (
        decisions["fantasy_team"]
        .apply(canonical_team)
    )

    missed = decisions[
        decisions["decision_type"]
        == "Should Have Started"
    ].copy()

    if missed.empty:
        return pd.DataFrame()

    summary = (
        missed.groupby(
            [
                "player",
                "player_position",
            ],
            as_index=False,
        )
        .agg(
            missed_start_count=(
                "player",
                "size",
            ),
            total_fantasy_points=(
                "fantasy_points",
                "sum",
            ),
            avg_fantasy_points=(
                "fantasy_points",
                "mean",
            ),
            max_fantasy_points=(
                "fantasy_points",
                "max",
            ),
        )
    )

    return summary.sort_values(
        [
            "missed_start_count",
            "total_fantasy_points",
        ],
        ascending=[
            False,
            False,
        ],
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 76)
    print("BUILDING BENCH DECISIONS ANALYSIS")
    print("=" * 76)

    team_week, decisions = load_data()

    print(
        f"\nLoaded {len(team_week):,} team-weeks."
    )

    print(
        f"Loaded {len(decisions):,} lineup decisions."
    )

    years = sorted(
        team_week["year"]
        .dropna()
        .astype(int)
        .unique()
    )

    print(
        "Years:",
        ", ".join(
            map(str, years)
        ),
    )

    team_week = add_opponent_score(
        team_week
    )

    missing_opponents = int(
        team_week[
            "opponent_score"
        ].isna().sum()
    )

    if missing_opponents:
        raise ValueError(
            f"{missing_opponents} team-weeks are missing "
            f"opponent scores."
        )

    team_week = add_outcome_metrics(
        team_week
    )

    franchise = build_franchise_summary(
        team_week
    )

    season = build_season_summary(
        team_week
    )

    player_summary = (
        build_player_decision_summary(
            decisions
        )
    )

    avoidable_losses = (
        team_week[
            team_week[
                "manager_caused_loss"
            ] == 1
        ]
        .copy()
        .sort_values(
            [
                "points_left_on_bench",
                "loss_margin",
            ],
            ascending=[
                False,
                True,
            ],
        )
    )

    biggest_bench_misses = (
        team_week
        .sort_values(
            "points_left_on_bench",
            ascending=False,
        )
        .copy()
    )


    # ========================================================
    # WRITE
    # ========================================================

    outputs = {
        "bench_decisions_team_week.csv":
            team_week,

        "bench_decisions_franchise.csv":
            franchise,

        "bench_decisions_season.csv":
            season,

        "bench_decisions_avoidable_losses.csv":
            avoidable_losses,

        "bench_decisions_biggest_misses.csv":
            biggest_bench_misses,

        "bench_decisions_player_summary.csv":
            player_summary,
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


    # ========================================================
    # VALIDATION
    # ========================================================

    print("\n" + "=" * 76)
    print("VALIDATION")
    print("=" * 76)

    assert len(team_week) == 1464

    assert (
        team_week[
            [
                "year",
                "week",
                "fantasy_team",
            ]
        ]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        team_week[
            "opponent_score"
        ]
        .notna()
        .all()
    )

    assert (
        team_week[
            "optimal_score"
        ]
        + 0.001
        >= team_week[
            "actual_score"
        ]
    ).all()

    actual_games = (
        team_week["actual_win"].sum()
        + 0.5
        * team_week["actual_tie"].sum()
    )

    print(
        f"PASS — {len(team_week):,} "
        f"unique team-weeks."
    )

    print(
        "PASS — every team-week has an opponent score."
    )

    print(
        "PASS — optimal score is never below actual score."
    )

    print(
        f"Actual win-equivalents represented: "
        f"{actual_games:.1f}"
    )


    # ========================================================
    # LEAGUE SUMMARY
    # ========================================================

    total_manager_losses = int(
        team_week[
            "manager_caused_loss"
        ].sum()
    )

    total_losses = int(
        team_week[
            "actual_loss"
        ].sum()
    )

    total_points_left = float(
        team_week[
            "points_left_on_bench"
        ].sum()
    )

    avg_points_left = float(
        team_week[
            "points_left_on_bench"
        ].mean()
    )

    print("\n" + "=" * 76)
    print("LEAGUE BENCH DECISION SUMMARY")
    print("=" * 76)

    print(
        f"Manager-caused losses: "
        f"{total_manager_losses}"
    )

    print(
        f"Total losses: "
        f"{total_losses}"
    )

    if total_losses:
        print(
            "Pct of losses avoidable with optimal lineup: "
            f"{total_manager_losses / total_losses * 100:.1f}%"
        )

    print(
        f"Total points left on bench: "
        f"{total_points_left:,.2f}"
    )

    print(
        f"Average points left per team-week: "
        f"{avg_points_left:.2f}"
    )

    print("\nMost manager-caused losses:")
    print(
        franchise[
            [
                "canonical_team",
                "team_weeks",
                "actual_wins",
                "actual_losses",
                "manager_caused_losses",
                "manager_caused_loss_rate",
                "avg_points_left_per_week",
                "avg_lineup_efficiency_pct",
            ]
        ]
        .head(15)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    print("\nWorst individual manager-caused losses:")
    print(
        avoidable_losses[
            [
                "year",
                "week",
                "canonical_team",
                "canonical_opponent",
                "actual_score",
                "opponent_score",
                "optimal_score",
                "loss_margin",
                "points_left_on_bench",
                "would_have_won_by",
                "should_have_benched",
                "should_have_started",
            ]
        ]
        .head(15)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    print("\nBiggest points-left-on-bench weeks:")
    print(
        biggest_bench_misses[
            [
                "year",
                "week",
                "canonical_team",
                "actual_score",
                "optimal_score",
                "points_left_on_bench",
                "actual_win",
                "manager_caused_loss",
                "should_have_benched",
                "should_have_started",
            ]
        ]
        .head(10)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )


if __name__ == "__main__":
    main()
