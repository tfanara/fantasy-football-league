from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

SOURCE_FILE = Path(
    "data/all_matchups_clean_2017_2025.csv"
)

OUT_DIR = Path("data/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MATRIX_LONG_FILE = (
    OUT_DIR / "schedule_swap_matrix_long.csv"
)

SEASON_FILE = (
    OUT_DIR / "schedule_swap_season.csv"
)

FRANCHISE_FILE = (
    OUT_DIR / "schedule_swap_franchise.csv"
)

EXTREMES_FILE = (
    OUT_DIR / "schedule_swap_extremes.csv"
)


# ============================================================
# HISTORICAL FRANCHISE ALIASES
# ============================================================

TEAM_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}


def canonical_team(team):
    if pd.isna(team):
        return team
    return TEAM_ALIASES.get(team, team)


# ============================================================
# HELPERS
# ============================================================

def record_result(score_for, score_against):
    if score_for > score_against:
        return 1.0, 0.0, 0.0

    if score_for < score_against:
        return 0.0, 1.0, 0.0

    return 0.0, 0.0, 1.0


# ============================================================
# LOAD
# ============================================================

print("=" * 90)
print("SCHEDULE SWAP ANALYSIS")
print("=" * 90)

if not SOURCE_FILE.exists():
    raise FileNotFoundError(SOURCE_FILE)

games = pd.read_csv(SOURCE_FILE)

print(f"\nSource games: {len(games):,}")


# ============================================================
# REGULAR SEASON ONLY
# ============================================================

if "is_playoffs" in games.columns:
    playoff_flag = (
        games["is_playoffs"]
        .astype(str)
        .str.lower()
        .eq("true")
    )

    games = games[
        ~playoff_flag
    ].copy()

print(
    f"Regular-season games: {len(games):,}"
)


# ============================================================
# CANONICALIZE TEAMS
# ============================================================

games["team_1_canonical"] = (
    games["team_1"].map(canonical_team)
)

games["team_2_canonical"] = (
    games["team_2"].map(canonical_team)
)


# ============================================================
# BUILD TEAM-WEEK TABLE
# ============================================================

side_1 = pd.DataFrame({
    "year": games["year"],
    "week": games["week"],
    "team": games["team_1_canonical"],
    "opponent": games["team_2_canonical"],
    "score": games["team_1_score"],
    "opponent_score": games["team_2_score"],
})

side_2 = pd.DataFrame({
    "year": games["year"],
    "week": games["week"],
    "team": games["team_2_canonical"],
    "opponent": games["team_1_canonical"],
    "score": games["team_2_score"],
    "opponent_score": games["team_1_score"],
})

team_week = pd.concat(
    [side_1, side_2],
    ignore_index=True,
)

team_week = (
    team_week
    .sort_values(
        ["year", "week", "team"]
    )
    .reset_index(drop=True)
)


# ============================================================
# BASIC VALIDATION
# ============================================================

duplicate_team_weeks = (
    team_week
    .duplicated(
        ["year", "week", "team"]
    )
    .sum()
)

print(
    f"Team-weeks: {len(team_week):,}"
)
print(
    f"Duplicate team-weeks: "
    f"{duplicate_team_weeks:,}"
)

if duplicate_team_weeks != 0:
    raise RuntimeError(
        "Duplicate team-week rows detected."
    )

season_team_counts = (
    team_week
    .groupby("year")["team"]
    .nunique()
)

print("\nTeams per season:")
print(
    season_team_counts.to_string()
)

if not season_team_counts.eq(12).all():
    raise RuntimeError(
        "Expected exactly 12 franchises "
        "in every season."
    )


# ============================================================
# LOOKUP TABLES
# ============================================================

score_lookup = {
    (
        int(row.year),
        int(row.week),
        row.team,
    ): float(row.score)
    for row in team_week.itertuples()
}

opponent_lookup = {
    (
        int(row.year),
        int(row.week),
        row.team,
    ): row.opponent
    for row in team_week.itertuples()
}


# ============================================================
# ACTUAL RECORDS
# ============================================================

actual_rows = []

for row in team_week.itertuples():

    win, loss, tie = record_result(
        float(row.score),
        float(row.opponent_score),
    )

    actual_rows.append({
        "year": int(row.year),
        "week": int(row.week),
        "team": row.team,
        "win": win,
        "loss": loss,
        "tie": tie,
    })

actual_week = pd.DataFrame(actual_rows)

actual_season = (
    actual_week
    .groupby(
        ["year", "team"],
        as_index=False,
    )
    .agg(
        actual_wins=("win", "sum"),
        actual_losses=("loss", "sum"),
        actual_ties=("tie", "sum"),
        games=("week", "count"),
    )
)


# ============================================================
# SCHEDULE SWAP SIMULATION
# ============================================================

swap_rows = []

years = sorted(
    team_week["year"].unique()
)

for year in years:

    year = int(year)

    year_data = team_week[
        team_week["year"].eq(year)
    ]

    teams = sorted(
        year_data["team"]
        .dropna()
        .unique()
        .tolist()
    )

    weeks = sorted(
        year_data["week"]
        .astype(int)
        .unique()
        .tolist()
    )

    if len(teams) != 12:
        raise RuntimeError(
            f"{year}: expected 12 teams; "
            f"found {len(teams)}"
        )

    for target_team in teams:

        for schedule_team in teams:

            wins = 0.0
            losses = 0.0
            ties = 0.0

            for week in weeks:

                target_key = (
                    year,
                    week,
                    target_team,
                )

                schedule_key = (
                    year,
                    week,
                    schedule_team,
                )

                target_score = (
                    score_lookup[target_key]
                )

                borrowed_opponent = (
                    opponent_lookup[schedule_key]
                )

                # --------------------------------------------
                # SELF-OPPONENT CORRECTION
                #
                # If target_team borrows schedule_team's
                # schedule and schedule_team actually faced
                # target_team that week, target_team should
                # face schedule_team — not itself.
                # --------------------------------------------

                if (
                    target_team != schedule_team
                    and
                    borrowed_opponent == target_team
                ):
                    simulated_opponent = (
                        schedule_team
                    )
                else:
                    simulated_opponent = (
                        borrowed_opponent
                    )

                opponent_key = (
                    year,
                    week,
                    simulated_opponent,
                )

                opponent_score = (
                    score_lookup[opponent_key]
                )

                win, loss, tie = record_result(
                    target_score,
                    opponent_score,
                )

                wins += win
                losses += loss
                ties += tie

            swap_rows.append({
                "year": year,
                "team": target_team,
                "schedule_team": schedule_team,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "games": len(weeks),
                "win_equivalent": (
                    wins + 0.5 * ties
                ),
                "is_actual_schedule": (
                    target_team
                    == schedule_team
                ),
            })


swap = pd.DataFrame(swap_rows)


# ============================================================
# VALIDATE ACTUAL-SCHEDULE DIAGONAL
# ============================================================

diagonal = (
    swap[
        swap["is_actual_schedule"]
    ]
    .merge(
        actual_season,
        on=["year", "team"],
        how="left",
        validate="one_to_one",
    )
)

diagonal["wins_match"] = np.isclose(
    diagonal["wins"],
    diagonal["actual_wins"],
)

diagonal["losses_match"] = np.isclose(
    diagonal["losses"],
    diagonal["actual_losses"],
)

diagonal["ties_match"] = np.isclose(
    diagonal["ties"],
    diagonal["actual_ties"],
)

diagonal_pass = (
    diagonal[
        [
            "wins_match",
            "losses_match",
            "ties_match",
        ]
    ]
    .all()
    .all()
)

print()
print("=" * 90)
print("ACTUAL-SCHEDULE DIAGONAL")
print("=" * 90)

print(
    "Actual record reconciliation:",
    "PASS" if diagonal_pass else "FAIL",
)

if not diagonal_pass:

    bad = diagonal[
        ~(
            diagonal["wins_match"]
            & diagonal["losses_match"]
            & diagonal["ties_match"]
        )
    ]

    print(
        bad[
            [
                "year",
                "team",
                "wins",
                "actual_wins",
                "losses",
                "actual_losses",
                "ties",
                "actual_ties",
            ]
        ].to_string(index=False)
    )

    raise RuntimeError(
        "Schedule-swap diagonal does not "
        "reproduce actual records."
    )


# ============================================================
# SEASON SUMMARY
# ============================================================

swap_stats = (
    swap
    .groupby(
        ["year", "team"],
        as_index=False,
    )
    .agg(
        average_schedule_wins=(
            "win_equivalent",
            "mean",
        ),
        best_schedule_wins=(
            "win_equivalent",
            "max",
        ),
        worst_schedule_wins=(
            "win_equivalent",
            "min",
        ),
        schedule_win_std=(
            "win_equivalent",
            "std",
        ),
        schedules_tested=(
            "schedule_team",
            "count",
        ),
    )
)

season = (
    actual_season
    .merge(
        swap_stats,
        on=["year", "team"],
        how="left",
        validate="one_to_one",
    )
)

season["actual_win_equivalent"] = (
    season["actual_wins"]
    + 0.5 * season["actual_ties"]
)

season["schedule_luck"] = (
    season["actual_win_equivalent"]
    - season["average_schedule_wins"]
)

season["schedule_range"] = (
    season["best_schedule_wins"]
    - season["worst_schedule_wins"]
)


# ============================================================
# BEST / WORST BORROWED SCHEDULE
# ============================================================

best_schedule = (
    swap
    .sort_values(
        [
            "year",
            "team",
            "win_equivalent",
            "schedule_team",
        ],
        ascending=[
            True,
            True,
            False,
            True,
        ],
    )
    .groupby(
        ["year", "team"],
        as_index=False,
    )
    .first()[
        [
            "year",
            "team",
            "schedule_team",
            "win_equivalent",
        ]
    ]
    .rename(
        columns={
            "schedule_team":
                "best_schedule_team",
            "win_equivalent":
                "best_schedule_record_wins",
        }
    )
)

worst_schedule = (
    swap
    .sort_values(
        [
            "year",
            "team",
            "win_equivalent",
            "schedule_team",
        ],
        ascending=[
            True,
            True,
            True,
            True,
        ],
    )
    .groupby(
        ["year", "team"],
        as_index=False,
    )
    .first()[
        [
            "year",
            "team",
            "schedule_team",
            "win_equivalent",
        ]
    ]
    .rename(
        columns={
            "schedule_team":
                "worst_schedule_team",
            "win_equivalent":
                "worst_schedule_record_wins",
        }
    )
)

season = (
    season
    .merge(
        best_schedule,
        on=["year", "team"],
        how="left",
        validate="one_to_one",
    )
    .merge(
        worst_schedule,
        on=["year", "team"],
        how="left",
        validate="one_to_one",
    )
)


# ============================================================
# SEASON LUCK RANKS
# ============================================================

season["schedule_luck_rank"] = (
    season
    .groupby("year")[
        "schedule_luck"
    ]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)

season["schedule_difficulty_rank"] = (
    season
    .groupby("year")[
        "schedule_luck"
    ]
    .rank(
        method="min",
        ascending=True,
    )
    .astype(int)
)


# ============================================================
# FRANCHISE ALL-TIME SUMMARY
# ============================================================

franchise = (
    season
    .groupby(
        "team",
        as_index=False,
    )
    .agg(
        seasons=("year", "nunique"),
        actual_wins=(
            "actual_win_equivalent",
            "sum",
        ),
        expected_wins_by_schedule=(
            "average_schedule_wins",
            "sum",
        ),
        total_schedule_luck=(
            "schedule_luck",
            "sum",
        ),
        avg_schedule_luck=(
            "schedule_luck",
            "mean",
        ),
        avg_schedule_range=(
            "schedule_range",
            "mean",
        ),
        most_helped_season=(
            "schedule_luck",
            "max",
        ),
        most_hurt_season=(
            "schedule_luck",
            "min",
        ),
    )
)

franchise["luck_rank"] = (
    franchise[
        "total_schedule_luck"
    ]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)

franchise["difficulty_rank"] = (
    franchise[
        "total_schedule_luck"
    ]
    .rank(
        method="min",
        ascending=True,
    )
    .astype(int)
)


# ============================================================
# EXTREME SEASONS
# ============================================================

most_helped = (
    season
    .sort_values(
        "schedule_luck",
        ascending=False,
    )
    .head(20)
    .copy()
)

most_helped["extreme_type"] = (
    "Most Helped"
)

most_hurt = (
    season
    .sort_values(
        "schedule_luck",
        ascending=True,
    )
    .head(20)
    .copy()
)

most_hurt["extreme_type"] = (
    "Most Hurt"
)

extremes = pd.concat(
    [
        most_helped,
        most_hurt,
    ],
    ignore_index=True,
)


# ============================================================
# FINAL VALIDATION
# ============================================================

expected_season_rows = 9 * 12
expected_swap_rows = 9 * 12 * 12

print()
print("=" * 90)
print("FINAL VALIDATION")
print("=" * 90)

print(
    f"Season-team rows: {len(season):,} "
    f"(expected {expected_season_rows:,})"
)

print(
    f"Schedule matrix rows: {len(swap):,} "
    f"(expected {expected_swap_rows:,})"
)

print(
    f"Franchises: {len(franchise):,}"
)

if len(season) != expected_season_rows:
    raise RuntimeError(
        "Unexpected season-team row count."
    )

if len(swap) != expected_swap_rows:
    raise RuntimeError(
        "Unexpected schedule matrix row count."
    )

if not swap["schedules_tested" if False else "year"].notna().all():
    raise RuntimeError(
        "Unexpected nulls in swap output."
    )

if not season[
    "schedules_tested"
].eq(12).all():
    raise RuntimeError(
        "Every team-season should test "
        "exactly 12 schedules."
    )


# ============================================================
# OUTPUT
# ============================================================

swap.to_csv(
    MATRIX_LONG_FILE,
    index=False,
)

season.to_csv(
    SEASON_FILE,
    index=False,
)

franchise.to_csv(
    FRANCHISE_FILE,
    index=False,
)

extremes.to_csv(
    EXTREMES_FILE,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=" * 90)
print("MOST SCHEDULE-HELPED TEAM-SEASONS")
print("=" * 90)

print(
    season[
        [
            "year",
            "team",
            "actual_win_equivalent",
            "average_schedule_wins",
            "schedule_luck",
        ]
    ]
    .sort_values(
        "schedule_luck",
        ascending=False,
    )
    .head(15)
    .to_string(index=False)
)

print()
print("=" * 90)
print("MOST SCHEDULE-HURT TEAM-SEASONS")
print("=" * 90)

print(
    season[
        [
            "year",
            "team",
            "actual_win_equivalent",
            "average_schedule_wins",
            "schedule_luck",
        ]
    ]
    .sort_values(
        "schedule_luck",
        ascending=True,
    )
    .head(15)
    .to_string(index=False)
)

print()
print("=" * 90)
print("ALL-TIME SCHEDULE LUCK")
print("=" * 90)

print(
    franchise[
        [
            "luck_rank",
            "team",
            "seasons",
            "actual_wins",
            "expected_wins_by_schedule",
            "total_schedule_luck",
            "avg_schedule_luck",
        ]
    ]
    .sort_values("luck_rank")
    .to_string(index=False)
)

print()
print("=" * 90)
print("OUTPUTS")
print("=" * 90)

print(MATRIX_LONG_FILE)
print(SEASON_FILE)
print(FRANCHISE_FILE)
print(EXTREMES_FILE)

print()
print(
    "PASS — SCHEDULE SWAP ANALYSIS BUILT"
)
